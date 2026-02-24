#!/usr/bin/env python3
"""monitor garage camera in loop"""

import configparser
import gc
import json
import logging
import signal
import sys
import time
from pathlib import Path

import paho.mqtt.client as paho
import psutil
import requests.exceptions
import sdnotify
from detect import detectframe, get_image, sanitize, save, sync_local_to_remote
from device import Device
from PIL import UnidentifiedImageError
from ultralytics import YOLO

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()

# Health monitoring thresholds
MEMORY_WARNING_THRESHOLD_MB = 500
INFERENCE_TIME_WARNING_MS = 300
HEARTBEAT_FILE = Path("/tmp/garagecam_heartbeat")


_process = psutil.Process()


def get_health_metrics():
    """Get current process health metrics."""
    return {
        "memory_mb": round(_process.memory_info().rss / 1024 / 1024, 1),
        "memory_percent": round(_process.memory_percent(), 1),
    }


def get_health_status(memory_mb, inference_ms, camera_ok):
    """Determine overall health status."""
    if not camera_ok:
        return "camera_error"
    if memory_mb > MEMORY_WARNING_THRESHOLD_MB or inference_ms > INFERENCE_TIME_WARNING_MS:
        return "degraded"
    return "healthy"


class GracefulKiller:
    """
    A class to handle graceful termination of a program.

    Attributes:
    -----------
    kill_now : bool
        A flag to indicate if the program should terminate.

    Methods:
    --------
    __init__():
        Initializes the signal handlers for SIGABRT, SIGINT, and SIGTERM.

    exit_gracefully(*args):
        Sets the kill_now flag to True to indicate that the program should terminate.
    """

    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGABRT, signal.SIG_DFL)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


def on_publish(client, userdata, mid, reason_codes, properties):
    log.info(f"on_publish({userdata},{mid})")


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    log.info(f"mqtt connected: {reason_code}")
    client.publish("garagecam/status", "online", retain=True)
    client.publish("garagecam/process/state", "running", retain=True)


def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        log.info("mqtt disconnected (clean)")
    else:
        log.warning(
            "mqtt disconnected unexpectedly: %s — will auto-reconnect", reason_code
        )


def on_message(mqtt_client, obj, msg):
    log.info("on_message()")


def get_section(config, section):
    """
    Retrieve a section from a configuration object and validate its existence.

    Args:
        config: A configparser-like object containing configuration sections
        section (str): The name of the section to retrieve

    Returns:
        dict-like object: The configuration section if it exists

    Raises:
        ValueError: If the specified section does not exist in the config

    Ensure that the specified section is present in the config.
    """
    if not config.has_section(section):
        raise ValueError(f"Missing required section: {section}")
    return config[section]


def main():
    sd = sdnotify.SystemdNotifier()
    sd.notify("STATUS=Loading")
    model = YOLO("best.pt")  # pretrained YOLOv8n model
    config = load_config()
    mqtt_config = get_section(config, "mqtt")
    lwt = "garagecam/status"
    mqtt_client = paho.Client(paho.CallbackAPIVersion.VERSION2, "garage-cam")
    mqtt_client.will_set(lwt, "offline", retain=True)
    mqtt_client.enable_logger(logger=log)
    mqtt_client.on_publish = on_publish
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.username_pw_set(mqtt_config["user"], mqtt_config["password"])
    log.info(
        "Connecting to MQTT broker at %s:%s", mqtt_config["host"], mqtt_config["port"]
    )
    mqtt_client.connect(mqtt_config["host"], int(mqtt_config["port"]))
    mqtt_client.subscribe("test")  # get on connect messages
    mqtt_client.loop_start()
    devices = list(
        map(lambda name: Device(name), ["Honda Civic", "Honda CR-V", "Garbage Bin"]),
    )
    for device in devices:
        j = {
            "name": device.name,
            "state_topic": f"{device.hass_name}/state",
            "device_class": "presence",
            "uniq_id": f"garagecam-{device.hass_name}",
            "availability_topic": lwt,
        }
        mqtt_client.publish(
            f"homeassistant/binary_sensor/{device.hass_name}/config",
            json.dumps(j),
            retain=True,
        )
    nfs_storage_config = {
        "name": "NFS Storage",
        "state_topic": "garagecam/nfs_storage/state",
        "device_class": "problem",
        "uniq_id": "garagecam-nfs_storage",
        "availability_topic": lwt,
    }
    mqtt_client.publish(
        "homeassistant/binary_sensor/garagecam-nfs_storage/config",
        json.dumps(nfs_storage_config),
        retain=True,
    )
    process_state_config = {
        "name": "Garagecam Process",
        "state_topic": "garagecam/process/state",
        "uniq_id": "garagecam-process",
        "availability_topic": lwt,
    }
    mqtt_client.publish(
        "homeassistant/sensor/garagecam-process/config",
        json.dumps(process_state_config),
        retain=True,
    )

    # Register health sensor with Home Assistant
    health_config = {
        "name": "Garage Cam Health",
        "state_topic": "garagecam/health",
        "value_template": "{{ value_json.status }}",
        "json_attributes_topic": "garagecam/health",
        "uniq_id": "garagecam-health",
        "availability_topic": lwt,
    }
    mqtt_client.publish(
        "homeassistant/sensor/garagecam_health/config",
        json.dumps(health_config),
        retain=True,
    )

    # curl -X GET -H "Authorization: Bearer config['hass']['token'] -H "Content-Type: application/json" http://homeassistant.home:8123/api/states/binary_sensor.garbage_bin_ha | python -m json.tool
    sd.notify("READY=1")
    sd.notify("STATUS=Running")
    killer = GracefulKiller()

    # Health monitoring state
    cycle_count = 0
    inference_times = []
    camera_ok = True
    img = None

    while not killer.kill_now:
        start = time.time()
        try:
            if img is not None:
                img.close()
                img = None
            objects, img = detectframe(model, get_image(config["camera"]))
            inference_ms = int((time.time() - start) * 1000)
            inference_times.append(inference_ms)
            camera_ok = True

            # Track inference time spikes
            if len(inference_times) > 1:
                avg_inference = sum(inference_times[-10:]) / min(len(inference_times), 10)
                if inference_ms > avg_inference * 1.5 and inference_ms > INFERENCE_TIME_WARNING_MS:
                    log.warning(
                        "Inference time spike: %dms (avg: %.0fms)",
                        inference_ms,
                        avg_inference,
                    )

            # Keep only recent inference times
            if len(inference_times) > 100:
                inference_times = inference_times[-50:]

            # Log health metrics periodically (every 10 cycles, ~2.5 minutes)
            cycle_count += 1
            if cycle_count % 10 == 0:
                metrics = get_health_metrics()
                log.info(
                    "Health: memory=%.1fMB (%.1f%%), inference=%dms",
                    metrics["memory_mb"],
                    metrics["memory_percent"],
                    inference_ms,
                )

                # Force garbage collection if memory is high
                if metrics["memory_mb"] > MEMORY_WARNING_THRESHOLD_MB:
                    log.warning(
                        "Memory usage high (%.1fMB), forcing garbage collection",
                        metrics["memory_mb"],
                    )
                    gc.collect()
                    metrics_after = get_health_metrics()
                    log.info(
                        "After GC: memory=%.1fMB (%.1f%%)",
                        metrics_after["memory_mb"],
                        metrics_after["memory_percent"],
                    )

                # Publish health status to MQTT
                health_payload = {
                    "memory_mb": metrics["memory_mb"],
                    "inference_ms": inference_ms,
                    "status": get_health_status(metrics["memory_mb"], inference_ms, camera_ok),
                }
                mqtt_client.publish("garagecam/health", json.dumps(health_payload))

            if "person" in objects and objects["person"] > 0.6:
                log.info("Skipping while person is in garage")
                gc.collect()
                continue
            if objects["something"] < 0.1:
                log.info("Nothing is in garage")
                # continue
            for device in devices:
                command = None
                if device.hass_name in objects:
                    command = device.update(objects[device.hass_name])
                else:
                    command = device.update(0.0)
                if command is not None:
                    nfs_ok = save(config["file"]["path"], img, sanitize(objects))
                    mqtt_client.publish(
                        "garagecam/nfs_storage/state",
                        "OFF" if nfs_ok else "ON",
                        retain=True,
                    )
                    mqtt_client.publish(
                        f"{device.hass_name}/state",
                        command.upper(),
                        retain=True,
                    )

            # Run garbage collection after each cycle to prevent memory buildup
            gc.collect()
        except UnidentifiedImageError:
            camera_ok = False
            log.warning("Failed to decode image from camera")
        except requests.exceptions.RequestException as e:
            camera_ok = False
            log.warning("Camera connection error: %s", e)
        except KeyboardInterrupt:
            break
        finally:
            sd.notify("WATCHDOG=1")
            HEARTBEAT_FILE.touch()
            delay = 15.0 - (time.time() - start)
            if delay > 0.0:
                time.sleep(delay)
        try:
            nfs_ok = sync_local_to_remote(config["file"]["path"])
            mqtt_client.publish(
                "garagecam/nfs_storage/state",
                "OFF" if nfs_ok else "ON",
                retain=True,
            )
        except Exception as e:
            log.warning("Failed to sync local files: %s", e)
    graceful_shutdown(mqtt_client, lwt, sd)


def graceful_shutdown(mqtt_client, lwt, sd):
    try:
        mqtt_client.publish("garagecam/process/state", "stopped", retain=True)
        publish_result = mqtt_client.publish(lwt, payload="offline", retain=True)
        publish_result.wait_for_publish(timeout=5)
    except (RuntimeError, ValueError, OSError) as e:
        log.warning("Could not publish offline status: %s", e)
    mqtt_client.disconnect()  # disconnect gracefully
    mqtt_client.loop_stop()  # stops network loop
    log.info("Gracefully exiting")
    sd.notify("STATUS=Graceful Exit")


def load_config():
    """
    Loads the configuration from a 'config.ini' file.

    This function reads the 'config.ini' file using the configparser module,
    logs the files read and the sections found in the configuration file,
    and returns the configuration object.

    Returns:
        configparser.ConfigParser: The configuration object containing the
        parsed configuration data.
    """
    config = configparser.ConfigParser()
    files_read = config.read("config.ini")
    log.info("Config files read: %s", files_read)
    log.info("Config sections: %s", config.sections())
    return config


if __name__ == "__main__":
    main()
