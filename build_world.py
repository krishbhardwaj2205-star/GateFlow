"""Recreate worlds/airport.wbt using basic Webots nodes only.

Run: python build_world.py
You normally just open the already generated world in Webots.
"""

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def box(name, position, size, color, extra=""):
    xyz = " ".join(map(str, position))
    dimensions = " ".join(map(str, size))
    rgb = " ".join(map(str, color))
    return f'''DEF {name} Pose {{
  translation {xyz}
  {extra}
  children [ Shape {{
    appearance PBRAppearance {{ baseColor {rgb} roughness 0.75 metalness 0 }}
    geometry Box {{ size {dimensions} }}
  }} ]
}}\n'''


def sign(text, position, size=0.28, color="0.85 0.92 1"):
    # Webots has no native Text/FontStyle nodes. Put text on a local PNG instead.
    # Pillow is included with the dashboard dependencies; textures ship ready-made.
    texture_name = re.sub(r"[^a-z0-9]+", "_", text.lower()) + ".png"
    folder = ROOT / "textures"
    folder.mkdir(exist_ok=True)
    image = Image.new("RGBA", (1024, 128), (12, 22, 36, 235))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 58)
    except OSError:
        font = ImageFont.load_default(size=58)
    bounds = draw.textbbox((0, 0), text, font=font)
    rgb = tuple(int(float(value) * 255) for value in color.split())
    draw.text(((1024 - bounds[2]) / 2, (128 - bounds[3] + bounds[1]) / 2 - bounds[1]),
              text, font=font, fill=rgb)
    image.save(folder / texture_name)
    xyz = " ".join(map(str, position))
    # Static signs face the initial camera. Billboard is not allowed under Pose.
    rotation = camera_rotation([10, -14, 15], for_sign=True)
    return f'''Pose {{ translation {xyz} rotation {rotation} children [
    Shape {{ appearance Appearance {{
      material Material {{ diffuseColor 1 1 1 emissiveColor 1 1 1 }}
      texture ImageTexture {{ url ["../textures/{texture_name}"] repeatS FALSE repeatT FALSE }}
    }}
      geometry Plane {{ size {size * 9:.3f} {size * 1.125:.3f} }}
    }}
] }}\n'''


def camera_rotation(eye, for_sign=False):
    """Point the camera at the origin with world Z up, using basic vector maths."""
    def unit(v):
        length = math.sqrt(sum(a * a for a in v))
        return [a / length for a in v]
    back = unit(eye)
    right = unit([-back[1], back[0], 0])
    up = [back[1] * right[2] - back[2] * right[1],
          back[2] * right[0] - back[0] * right[2],
          back[0] * right[1] - back[1] * right[0]]
    # Webots uses camera X forward, Y left, Z up. A Plane uses X right, Y up.
    axes = (right, up, back) if for_sign else (
        [-v for v in back], [-v for v in right], up)
    matrix = [[axis[i] for axis in axes] for i in range(3)]
    angle = math.acos((sum(matrix[i][i] for i in range(3)) - 1) / 2)
    axis = unit([matrix[2][1] - matrix[1][2], matrix[0][2] - matrix[2][0],
                 matrix[1][0] - matrix[0][1]])
    return " ".join(f"{v:.8f}" for v in axis + [angle])


def build():
    eye = [10, -14, 15]
    world = ['''#VRML_SIM R2025a utf8
# Group 24: kinematic conveyor simulation with virtual tag/checkpoint sensors.
WorldInfo { title "GateFlow - Smart Airport Baggage Handling" basicTimeStep 32 coordinateSystem "ENU" }
''', f'Viewpoint {{ orientation {camera_rotation(eye)} position 10 -14 15 fieldOfView 0.90 }}\n',
             'Background { skyColor [0.025 0.045 0.075] }\n',
             'DirectionalLight { direction -0.35 -0.20 -1 intensity 2 ambientIntensity 0.65 }\n',
             'DirectionalLight { direction 0.4 0.8 -0.4 intensity 0.8 }\n']
    world.append(box("FLOOR", [0, 0, -0.12], [18, 12, 0.2], [0.06, 0.09, 0.14]))
    world.append(box("MAIN_BELT", [0, 0, 0.6], [11.6, 1.15, 0.1], [0.16, 0.20, 0.27]))
    world.append(box("DELHI_BELT", [-1, -1.85, 0.6], [1.15, 3.7, 0.1], [0.12, 0.22, 0.31]))
    world.append(box("MUMBAI_BELT", [1.6, 1.85, 0.6], [1.15, 3.7, 0.1], [0.28, 0.21, 0.15]))
    for index in range(18):
        world.append(box(f"SLAT_{index}", [-5.65 + index * 0.62, 0, 0.658], [0.045, 1.08, 0.012], [0.38, 0.45, 0.55]))
    for y in [-0.62, 0.62]:
        # Rails leave transfer gaps at the two diverters.
        for start, end in [(-5.8, -1.6), (-0.4, 1.0), (2.2, 5.8)]:
            world.append(box(f"RAIL_{len(world)}", [(start + end) / 2, y, 0.76], [end - start, 0.06, 0.12], [0.43, 0.50, 0.60]))
    for x in [-5, -3, -1, 1.6, 3.5, 5.3]:
        world.append(box(f"LEG_{len(world)}", [x, 0, 0.28], [0.18, 0.75, 0.55], [0.28, 0.34, 0.43]))
    for x, y in [(-1, -1.7), (-1, -3.1), (1.6, 1.7), (1.6, 3.1)]:
        world.append(box(f"LEG_{len(world)}", [x, y, 0.28], [0.75, 0.18, 0.55], [0.28, 0.34, 0.43]))
    for y in [-0.63, 0.63]:
        world.append(box(f"SCANNER_POST_{len(world)}", [-3.9, y, 1.0], [0.13, 0.13, 0.85], [0.09, 0.70, 0.77]))
    world.append(box("SCANNER_BAR", [-3.9, 0, 1.42], [0.17, 1.4, 0.16], [0.09, 0.70, 0.77]))
    world.append(sign("TAG IDENTIFICATION", [-3.9, 0, 1.9], 0.24))
    for gate, x in [("A", -1), ("B", 1.6)]:
        world.append(box("DIVERTER_" + gate, [x, 0.10, 0.89], [0.85, 0.10, 0.14], [0.96, 0.77, 0.18], "rotation 0 0 1 0"))
    gates = [("A", "DELHI", [-1, -3.0, 0.7], [0.12, 0.65, 0.95]),
             ("B", "MUMBAI", [1.6, 3.0, 0.7], [0.92, 0.47, 0.12]),
             ("C", "BENGALURU", [5.2, 0, 0.7], [0.25, 0.78, 0.45])]
    for gate, city, position, color in gates:
        x, y, z = position
        # Checkpoint lamps turn red if that branch receives the wrong bag.
        world.append(f'''Pose {{ translation {x} {y} 1.55 children [ Shape {{
  appearance DEF BEACON_{gate} PBRAppearance {{ baseColor {" ".join(map(str, color))} roughness 0.5 metalness 0 }}
  geometry Sphere {{ radius 0.12 }}
}} ] }}\n''')
        dimensions = [1.13, 0.035, 0.025] if gate != "C" else [0.035, 1.13, 0.025]
        world.append(box("SENSOR_" + gate, position, dimensions, color))
        world.append(sign(f"GATE {gate} - {city}", [x, y, 2.05], 0.29))
    world.append(box("COLLECTION_A", [-1, -3.95, 0.6], [2.3, 1.5, 0.1], [0.09, 0.29, 0.42]))
    world.append(box("COLLECTION_B", [1.6, 3.95, 0.6], [2.3, 1.5, 0.1], [0.38, 0.25, 0.12]))
    world.append(box("COLLECTION_C", [6.10, 0, 0.6], [1.7, 2.3, 0.1], [0.12, 0.31, 0.20]))
    world.append(box("INSPECTION", [-4.85, 3.95, 0.6], [2.3, 1.5, 0.1], [0.36, 0.10, 0.16]))
    world.append(sign("MANUAL INSPECTION", [-4.85, 3.95, 1.7], 0.25, "1 0.45 0.48"))
    world.append(sign("CHECK-IN", [-5.4, -0.9, 1.2], 0.29))
    world.append('Robot { name "Airport Supervisor" controller "baggage_controller" supervisor TRUE }\n')
    output = ROOT / "worlds" / "airport.wbt"
    output.parent.mkdir(exist_ok=True)
    output.write_text("".join(world), encoding="utf-8")
    print(f"Created {output}")


if __name__ == "__main__":
    build()
