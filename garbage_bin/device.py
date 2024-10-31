import logging

log = logging.getLogger()


class Device:
    """hold object state and ST reference"""

    def __init__(self, name):
        self.name = name
        self.ssd_name = name.lower().replace("-", "")
        self.hass_name = self.ssd_name.replace(" ", "_")
        self.value = 0.8
        self.status = "unknown"

    def update(self, value):
        old_value = self.value
        self.value = old_value * 0.7 + value * 0.3
        if self.value < 0.6 and self.status != "off":
            log.info(
                f"{self.name} departed {value:.3f}+{old_value:.3f}=>{self.value:.3f}",
            )
            self.status = "off"
            return "off"
        if self.value > 0.9 and self.status != "on":
            log.info(
                f"{self.name} arrived {value:.3f}+{old_value:.3f}=>{self.value:.3f}",
            )
            self.status = "on"
            return "on"
        if abs(self.value - old_value) > 0.0005:
            log.info(
                f"{self.name} updated {value:.3f}+{old_value:.3f}=>{self.value:.3f}",
            )
        return None
