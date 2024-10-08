import logging


log = logging.getLogger()


class Device(object):
    """
    hold object state and ST reference
    """

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
                "{} departed {:.3f}+{:.3f}=>{:.3f}".format(
                    self.name, value, old_value, self.value
                )
            )
            self.status = "off"
            return "off"
        elif self.value > 0.9 and self.status != "on":
            log.info(
                "{} arrived {:.3f}+{:.3f}=>{:.3f}".format(
                    self.name, value, old_value, self.value
                )
            )
            self.status = "on"
            return "on"
        elif abs(self.value - old_value) > 0.0005:
            log.info(
                "{} updated {:.3f}+{:.3f}=>{:.3f}".format(
                    self.name, value, old_value, self.value
                )
            )
        return None
