"""Gera prato.glb em escala real (metros): prato de 27 cm de diâmetro, borda elevada.
Sem dependências: escreve o binário GLB (glTF 2.0) direto com struct."""
import json
import math
import struct

DIAMETRO_M = 0.27          # medir o prato real do restaurante e ajustar aqui
RAIO = DIAMETRO_M / 2
ALTURA_BORDA = 0.02        # 2 cm de borda
SEGMENTOS = 64

# Perfil (raio, altura) de fora para dentro: base plana + borda curva
perfil = [
    (0.0, 0.0),
    (RAIO * 0.62, 0.0),
    (RAIO * 0.70, 0.006),
    (RAIO * 0.86, ALTURA_BORDA * 0.6),
    (RAIO, ALTURA_BORDA),
    (RAIO * 0.99, ALTURA_BORDA * 0.7),
]

positions, normals, indices = [], [], []
for i in range(SEGMENTOS):
    a = 2 * math.pi * i / SEGMENTOS
    ca, sa = math.cos(a), math.sin(a)
    for (r, y) in perfil:
        positions.append((r * ca, y, r * sa))
        normals.append((0.0, 1.0, 0.0))  # normais simplificadas (prato liso)

anel = len(perfil)
for i in range(SEGMENTOS):
    j = (i + 1) % SEGMENTOS
    for k in range(anel - 1):
        a0 = i * anel + k
        a1 = i * anel + k + 1
        b0 = j * anel + k
        b1 = j * anel + k + 1
        indices += [a0, b0, a1, a1, b0, b1]

# Empacota buffers
bin_pos = b"".join(struct.pack("<3f", *p) for p in positions)
bin_nrm = b"".join(struct.pack("<3f", *n) for n in normals)
bin_idx = b"".join(struct.pack("<I", i) for i in indices)
bin_idx += b"\x00" * ((4 - len(bin_idx) % 4) % 4)
buffer = bin_pos + bin_nrm + bin_idx

xs = [p[0] for p in positions]
ys = [p[1] for p in positions]
zs = [p[2] for p in positions]

gltf = {
    "asset": {"version": "2.0", "generator": "prototipo-ar"},
    "scene": 0,
    "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0, "name": "prato"}],
    "meshes": [{"primitives": [{
        "attributes": {"POSITION": 0, "NORMAL": 1},
        "indices": 2,
        "material": 0,
    }]}],
    "materials": [{
        "name": "porcelana",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.93, 0.92, 0.89, 1.0],
            "metallicFactor": 0.0,
            "roughnessFactor": 0.35,
        },
        "doubleSided": True,
    }],
    "accessors": [
        {"bufferView": 0, "componentType": 5126, "count": len(positions),
         "type": "VEC3", "min": [min(xs), min(ys), min(zs)],
         "max": [max(xs), max(ys), max(zs)]},
        {"bufferView": 1, "componentType": 5126, "count": len(normals), "type": "VEC3"},
        {"bufferView": 2, "componentType": 5125, "count": len(indices), "type": "SCALAR"},
    ],
    "bufferViews": [
        {"buffer": 0, "byteOffset": 0, "byteLength": len(bin_pos), "target": 34962},
        {"buffer": 0, "byteOffset": len(bin_pos), "byteLength": len(bin_nrm), "target": 34962},
        {"buffer": 0, "byteOffset": len(bin_pos) + len(bin_nrm), "byteLength": len(bin_idx), "target": 34963},
    ],
    "buffers": [{"byteLength": len(buffer)}],
}

json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)

total = 12 + 8 + len(json_bytes) + 8 + len(buffer)
with open("prato.glb", "wb") as f:
    f.write(struct.pack("<4sII", b"glTF", 2, total))
    f.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
    f.write(json_bytes)
    f.write(struct.pack("<I4s", len(buffer), b"BIN\x00"))
    f.write(buffer)

print(f"prato.glb ok: {total} bytes, {len(positions)} vértices, {len(indices)//3} triângulos")
