# Interfaces with neato command line.

import serial_api as control

from programs import log
from rate import Rate
from swig import pru

import robot_status

# Initialize pru. (It's okay if this runs more than once.)
if not pru.Init():
  raise RuntimeError("PRU initialization failed.")


# Represents LDS sensor, and allows user to control it.
class LDS:
  def __init__(self):
    self.ready = False

    control.send_command("SetLDSRotation on")

  def __del__(self):
    control.send_command("SetLDSRotation off")

  # Wait for sensor to spin up.
  def __spin_up(self):
    if not self.ready:
      log.info("Waiting for LDS spinup.")
      rate = Rate()

      # Wait for a valid packet.
      while True:
        rate.rate(0.01)

        scan = self.__get_scan()
        if len(scan.keys()) > 1:
          break

      self.ready = True

      log.info("LDS ready.")

  # Helper to get and parse a complete scan packet.
  def __get_scan(self, *args, **kwargs):
    packet = control.get_output("GetLDSScan", *args, **kwargs)

    # Get rid of help message.
    packet.pop("AngleInDegrees", None)

    # Add rotation speed.
    ret = {}
    ret["ROTATION_SPEED"] = float(packet["ROTATION_SPEED"])
    packet.pop("ROTATION_SPEED", None)

    # Discard any errors.
    for key in packet.keys():
      if int(packet[key][2]) == 0:
        # Convert the angle so that 0 deg is to the right, not up.
        angle = int(key)
        real_angle = angle + 90
        if real_angle > 359:
          real_angle -= 359

        ret[real_angle] = [int(x) for x in packet[key]]
      else:
        log.debug("Error %s in LDS reading for angle %s." % \
            (packet[key][2], key))

    return ret

  # Returns a usable scan packet to the user.
  def get_scan(self, *args, **kwargs):
    # Make sure sensor is ready.
    self.__spin_up()

    packet = self.__get_scan(*args, **kwargs)
    packet.pop("ROTATION_SPEED", None);
    return packet

  @staticmethod
  # Returns whether lds is active and ready to transmit data.
  def is_active():
    info = control.get_output("GetMotors")
    mvolts = int(info["Laser_mVolts"])
    return bool(mvolts)

  # Returns the rotation speed of the LDS sensor.
  def rotation_speed(self):
    if not self.is_active():
      return 0

    return self.__get_scan()["ROTATION_SPEED"]


# A class for the analog sensors.
class Analog:
  def __get_sensors(self, **kwargs):
    return control.get_output("GetAnalogSensors", **kwargs)

  # Gets readings from the drop sensors.
  def drop(self, **kwargs):
    left = pru.GetLeftDrop()
    right = pru.GetRightDrop()

    if (left < 0 or right < 0):
      log.error("Getting drop sensor readings failed.")
      raise ValueError("Getting drop sensor readings failed.")

    return (left, right)

  # Returns the battery voltage.
  def battery_voltage(self, **kwargs):
    info = self.__get_sensors(**kwargs)
    voltage = int(info["BatteryVoltageInmV"])

    return voltage

  # Return the charging voltage.
  def charging(self, **kwargs):
    info = self.__get_sensors(**kwargs)
    voltage = int(info["ChargeVoltInmV"])

    return voltage


class Digital:
  def __get_sensors(self, **kwargs):
    return control.get_output("GetDigitalSensors", **kwargs)

  # Returns whether or not the wheels are extended.
  def wheels_extended(self, **kwargs):
    info = self.__get_sensors(**kwargs)
    left = bool(int(info["SNSR_LEFT_WHEEL_EXTENDED"]))
    right = bool(int(info["SNSR_RIGHT_WHEEL_EXTENDED"]))

    return (left, right)
