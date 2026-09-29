"""標準ライブラリだけで Caliboo マスコットの OBJ/MTL を生成・検証する。"""

from __future__ import annotations

import argparse
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT / "frontend/src/assets/takeuchi"
MATERIALS = {
    "mint": (0.55, 0.88, 0.77),
    "dark": (0.11, 0.18, 0.17),
    "white": (1.0, 1.0, 1.0),
    "pink": (0.98, 0.63, 0.72),
}


class Mesh:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[str, tuple[int, int, int]]] = []

    def vertex(self, xyz: tuple[float, float, float]) -> int:
        self.vertices.append(xyz)
        return len(self.vertices)

    def face(self, material: str, a: int, b: int, c: int) -> None:
        self.faces.append((material, (a, b, c)))

    def ellipsoid(
        self,
        material: str,
        center: tuple[float, float, float],
        radii: tuple[float, float, float],
        tilt: float = 0.0,
        latitude: int = 18,
        longitude: int = 32,
    ) -> None:
        rings: list[list[int]] = []
        cosine, sine = math.cos(tilt), math.sin(tilt)

        def point(x: float, y: float, z: float) -> int:
            return self.vertex((center[0] + x * cosine - y * sine,
                                center[1] + x * sine + y * cosine,
                                center[2] + z))

        bottom = point(0, -radii[1], 0)
        for row in range(1, latitude):
            phi = -math.pi / 2 + math.pi * row / latitude
            ring = []
            for column in range(longitude):
                theta = 2 * math.pi * column / longitude
                ring.append(point(radii[0] * math.cos(phi) * math.cos(theta),
                                  radii[1] * math.sin(phi),
                                  radii[2] * math.cos(phi) * math.sin(theta)))
            rings.append(ring)
        top = point(0, radii[1], 0)
        for column in range(longitude):
            next_column = (column + 1) % longitude
            self.face(material, bottom, rings[0][next_column], rings[0][column])
            for row in range(len(rings) - 1):
                a, b = rings[row][column], rings[row][next_column]
                c, d = rings[row + 1][column], rings[row + 1][next_column]
                self.face(material, a, b, c)
                self.face(material, b, d, c)
            self.face(material, rings[-1][column], rings[-1][next_column], top)

    def smile(self) -> None:
        """顔の前面に沿う、少し下がったU字の立体チューブ。"""
        rings: list[list[int]] = []
        segments, sides = 20, 8
        for segment in range(segments + 1):
            x = -0.19 + 0.38 * segment / segments
            y = -0.265 - 0.09 * (1 - (x / 0.19) ** 2)
            z = 0.51
            slope = 2 * 0.09 * x / (0.19 ** 2)
            length = math.hypot(1, slope)
            ring = []
            for side in range(sides):
                angle = 2 * math.pi * side / sides
                radius = 0.017
                ring.append(self.vertex((x - radius * math.cos(angle) * slope / length,
                                         y + radius * math.cos(angle) / length,
                                         z + radius * math.sin(angle))))
            rings.append(ring)
        for segment in range(segments):
            for side in range(sides):
                next_side = (side + 1) % sides
                a, b = rings[segment][side], rings[segment][next_side]
                c, d = rings[segment + 1][side], rings[segment + 1][next_side]
                self.face("dark", a, b, c)
                self.face("dark", b, d, c)


def build() -> Mesh:
    mesh = Mesh()
    mesh.ellipsoid("mint", (-0.54, 0.65, -0.06), (0.21, 0.38, 0.18), 0.26)
    mesh.ellipsoid("mint", (0.54, 0.65, -0.06), (0.21, 0.38, 0.18), -0.26)
    mesh.ellipsoid("mint", (0, 0, 0), (0.87, 0.82, 0.55))
    for side in (-1, 1):
        mesh.ellipsoid("dark", (side * 0.29, 0.09, 0.525), (0.105, 0.13, 0.055))
        mesh.ellipsoid("white", (side * 0.29 - 0.027, 0.135, 0.579),
                       (0.029, 0.031, 0.011), latitude=10, longitude=16)
        mesh.ellipsoid("pink", (side * 0.52, -0.20, 0.429),
                       (0.13, 0.064, 0.023), latitude=12, longitude=20)
    mesh.smile()
    return mesh


def export(mesh: Mesh, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["# Caliboo mascot; coordinates: Y up, Z forward", "mtllib mascot.mtl"]
    lines.extend(f"v {x:.8f} {y:.8f} {z:.8f}" for x, y, z in mesh.vertices)
    last_material = None
    for material, indices in mesh.faces:
        if material != last_material:
            lines.append(f"usemtl {material}")
            last_material = material
        lines.append("f " + " ".join(map(str, indices)))
    (directory / "mascot.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")
    mtl = ["# Diffuse colors for the Caliboo mascot"]
    for name, color in MATERIALS.items():
        mtl.extend((f"newmtl {name}", "Kd " + " ".join(f"{value:.3f}" for value in color)))
    (directory / "mascot.mtl").write_text("\n".join(mtl) + "\n", encoding="utf-8")


def verify(directory: Path) -> tuple[int, int]:
    """書き出したテキストを再読込し、座標と三角形参照を調べる。"""
    obj = (directory / "mascot.obj").read_text(encoding="utf-8")
    mtl = (directory / "mascot.mtl").read_text(encoding="utf-8")
    names = {line.split()[1] for line in mtl.splitlines() if line.startswith("newmtl ")}
    vertices: list[tuple[float, float, float]] = []
    faces = 0
    active_material = ""
    for line in obj.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            assert len(parts) == 4
            values = tuple(float(value) for value in parts[1:])
            assert all(math.isfinite(value) for value in values)
            vertices.append(values)
        elif parts[0] == "usemtl":
            assert len(parts) == 2 and parts[1] in names
            active_material = parts[1]
        elif parts[0] == "f":
            assert active_material and len(parts) == 4
            indices = [int(value) for value in parts[1:]]
            assert len(set(indices)) == 3
            assert all(1 <= index <= len(vertices) for index in indices)
            a, b, c = (vertices[index - 1] for index in indices)
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            cross = (u[1] * v[2] - u[2] * v[1],
                     u[2] * v[0] - u[0] * v[2],
                     u[0] * v[1] - u[1] * v[0])
            assert sum(component * component for component in cross) > 1e-16
            faces += 1
    assert vertices and faces and names == set(MATERIALS)
    return len(vertices), faces


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only:
        mesh = build()
        export(mesh, MODEL_DIR)
        export(mesh, WEB_DIR)
    for directory in (MODEL_DIR, WEB_DIR):
        count = verify(directory)
        print(f"{directory.relative_to(ROOT)}: {count[0]} vertices, {count[1]} faces; valid")


if __name__ == "__main__":
    main()
