import hashlib

ARENA_XML = r"""
<mujoco model="yurei_mujoco_lab">
  <compiler angle="radian"/>
  <option timestep="0.01" gravity="0 0 -9.81" integrator="RK4"/>
  <visual><global azimuth="135" elevation="-35"/></visual>
  <default>
    <geom friction="0.8 0.1 0.1" rgba="0.28 0.32 0.40 1"/>
  </default>
  <worldbody>
    <light pos="0 0 8" diffuse="0.8 0.8 0.8"/>
    <geom name="floor" type="plane" size="7 7 0.1" rgba="0.035 0.045 0.065 1"/>
    <geom name="goal" type="cylinder" pos="4 4 0.02" size="1.1 0.02" contype="0" conaffinity="0" rgba="0.25 0.85 0.65 0.32"/>
    <geom name="wall_a" type="box" pos="0 1.5 0.5" size="2.0 0.25 0.5" rgba="0.30 0.23 0.42 1"/>
    <geom name="wall_b" type="box" pos="-2.7 -1.0 0.5" size="0.25 1.5 0.5" rgba="0.30 0.23 0.42 1"/>
    <geom name="resource_a" type="sphere" pos="-4 4 0.3" size="0.3" rgba="0.95 0.65 0.22 1"/>
    <geom name="resource_b" type="sphere" pos="4 -4 0.3" size="0.3" rgba="0.95 0.65 0.22 1"/>
    <geom name="resource_c" type="sphere" pos="-4 -4 0.3" size="0.3" rgba="0.95 0.65 0.22 1"/>
    <body name="agent" pos="0 0 0.35">
      <joint name="x" type="slide" axis="1 0 0" range="-6 6" damping="2"/>
      <joint name="y" type="slide" axis="0 1 0" range="-6 6" damping="2"/>
      <geom name="agent_geom" type="sphere" size="0.35" mass="1" rgba="0.55 0.32 1 1"/>
      <site name="agent_site" size="0.08" rgba="1 1 1 1"/>
    </body>
    <site name="landmark_nw" pos="-5 5 0.1" size="0.12" rgba="0.3 0.8 1 1"/>
    <site name="landmark_ne" pos="5 5 0.1" size="0.12" rgba="0.3 0.8 1 1"/>
    <site name="landmark_sw" pos="-5 -5 0.1" size="0.12" rgba="0.3 0.8 1 1"/>
    <site name="landmark_se" pos="5 -5 0.1" size="0.12" rgba="0.3 0.8 1 1"/>
  </worldbody>
  <actuator>
    <motor name="motor_x" joint="x" gear="1" ctrlrange="-8 8" ctrllimited="true"/>
    <motor name="motor_y" joint="y" gear="1" ctrlrange="-8 8" ctrllimited="true"/>
  </actuator>
</mujoco>
""".strip()


def arena_digest() -> str:
    return hashlib.sha256(ARENA_XML.encode()).hexdigest()
