"""Gera os arquivos de AR do prato em escala real (1 unidade = 1 metro):
  - prato.glb  -> Android (Scene Viewer)
  - prato.usdz -> iPhone (AR Quick Look)
  - prato.jpg  -> textura (também usada como miniatura)
A foto (prato_src.jpg, vista de cima) é recortada no círculo do prato e aplicada num disco de 27 cm.
"""
import io
import json
import math
import struct
import zlib

from PIL import Image

DIAMETRO_M = 0.27          # medir o prato real do restaurante e ajustar aqui
RAIO = DIAMETRO_M / 2
SEGMENTOS = 128
ESPESSURA = 0.012          # 1,2 cm: prato com volume, não uma folha

# ---------- textura: recorte quadrado centrado no prato ----------
img = Image.open("prato_src.jpg").convert("RGB")
W, H = img.size
# prato ocupa ~ x 105..1080 e y 165..1135 na foto de 1200 px
cx, cy, r = 592, 650, 488
recorte = img.crop((cx - r, cy - r, cx + r, cy + r)).resize((1024, 1024), Image.LANCZOS)
recorte.save("prato.jpg", quality=88)
textura_bytes = io.BytesIO()
recorte.save(textura_bytes, format="JPEG", quality=88)
textura_bytes = textura_bytes.getvalue()


def uv(x, z):
    return (0.5 + x / (2 * RAIO), 0.5 - z / (2 * RAIO))


# ---------- geometria: disco com borda (topo + lateral + base) ----------
pos, nrm, uvs, idx = [], [], [], []


def add(p, n, t):
    pos.append(p)
    nrm.append(n)
    uvs.append(t)
    return len(pos) - 1


# topo: centro + anel
topo_c = add((0.0, ESPESSURA, 0.0), (0, 1, 0), uv(0, 0))
topo_ring = []
for i in range(SEGMENTOS):
    a = 2 * math.pi * i / SEGMENTOS
    x, z = RAIO * math.cos(a), RAIO * math.sin(a)
    topo_ring.append(add((x, ESPESSURA, z), (0, 1, 0), uv(x, z)))
for i in range(SEGMENTOS):
    j = (i + 1) % SEGMENTOS
    idx += [topo_c, topo_ring[j], topo_ring[i]]

# lateral (normais para fora)
for i in range(SEGMENTOS):
    j = (i + 1) % SEGMENTOS
    a0 = 2 * math.pi * i / SEGMENTOS
    a1 = 2 * math.pi * j / SEGMENTOS
    p0 = (RAIO * math.cos(a0), 0.0, RAIO * math.sin(a0))
    p1 = (RAIO * math.cos(a1), 0.0, RAIO * math.sin(a1))
    p2 = (RAIO * math.cos(a1), ESPESSURA, RAIO * math.sin(a1))
    p3 = (RAIO * math.cos(a0), ESPESSURA, RAIO * math.sin(a0))
    n0 = (math.cos(a0), 0, math.sin(a0))
    n1 = (math.cos(a1), 0, math.sin(a1))
    v0 = add(p0, n0, (0.0, 0.5))
    v1 = add(p1, n1, (0.0, 0.5))
    v2 = add(p2, n1, (0.0, 0.5))
    v3 = add(p3, n0, (0.0, 0.5))
    idx += [v0, v1, v2, v0, v2, v3]

# base (cor neutra, escondida na mesa)
base_c = add((0.0, 0.0, 0.0), (0, -1, 0), (0.5, 0.5))
base_ring = []
for i in range(SEGMENTOS):
    a = 2 * math.pi * i / SEGMENTOS
    base_ring.append(add((RAIO * math.cos(a), 0.0, RAIO * math.sin(a)), (0, -1, 0), (0.5, 0.5)))
for i in range(SEGMENTOS):
    j = (i + 1) % SEGMENTOS
    idx += [base_c, base_ring[i], base_ring[j]]

# ---------- GLB ----------
bin_pos = b"".join(struct.pack("<3f", *p) for p in pos)
bin_nrm = b"".join(struct.pack("<3f", *n) for n in nrm)
bin_uv = b"".join(struct.pack("<2f", *t) for t in uvs)
bin_idx = b"".join(struct.pack("<I", i) for i in idx)
bin_idx += b"\x00" * ((4 - len(bin_idx) % 4) % 4)
bin_tex = textura_bytes + b"\x00" * ((4 - len(textura_bytes) % 4) % 4)

offs, cursor = {}, 0
for nome, dados in [("pos", bin_pos), ("nrm", bin_nrm), ("uv", bin_uv), ("idx", bin_idx), ("tex", bin_tex)]:
    offs[nome] = (cursor, len(dados))
    cursor += len(dados)
buffer = bin_pos + bin_nrm + bin_uv + bin_idx + bin_tex

xs = [p[0] for p in pos]
ys = [p[1] for p in pos]
zs = [p[2] for p in pos]

gltf = {
    "asset": {"version": "2.0", "generator": "prototipo-ar"},
    "scene": 0,
    "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0, "name": "prato"}],
    "meshes": [{"primitives": [{
        "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
        "indices": 3,
        "material": 0,
    }]}],
    "materials": [{
        "name": "prato",
        "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0},
            "metallicFactor": 0.0,
            "roughnessFactor": 0.45,
        },
        "doubleSided": False,
    }],
    "textures": [{"source": 0}],
    "images": [{"bufferView": 4, "mimeType": "image/jpeg"}],
    "accessors": [
        {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
         "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
        {"bufferView": 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
        {"bufferView": 2, "componentType": 5126, "count": len(uvs), "type": "VEC2"},
        {"bufferView": 3, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
    ],
    "bufferViews": [
        {"buffer": 0, "byteOffset": offs["pos"][0], "byteLength": offs["pos"][1], "target": 34962},
        {"buffer": 0, "byteOffset": offs["nrm"][0], "byteLength": offs["nrm"][1], "target": 34962},
        {"buffer": 0, "byteOffset": offs["uv"][0], "byteLength": offs["uv"][1], "target": 34962},
        {"buffer": 0, "byteOffset": offs["idx"][0], "byteLength": offs["idx"][1], "target": 34963},
        {"buffer": 0, "byteOffset": offs["tex"][0], "byteLength": len(textura_bytes)},
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
print(f"prato.glb: {total} bytes, {len(pos)} vértices")

# ---------- USDZ (iPhone) ----------
usda = f"""#usda 1.0
(
    defaultPrim = "Prato"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "Prato"
{{
    def Mesh "Disco"
    {{
        point3f[] points = [{", ".join(f"({p[0]:.5f}, {p[1]:.5f}, {p[2]:.5f})" for p in pos)}]
        int[] faceVertexCounts = [{", ".join("3" for _ in range(len(idx) // 3))}]
        int[] faceVertexIndices = [{", ".join(str(i) for i in idx)}]
        normal3f[] normals = [{", ".join(f"({n[0]:.3f}, {n[1]:.3f}, {n[2]:.3f})" for n in nrm)}] (
            interpolation = "vertex"
        )
        texCoord2f[] primvars:st = [{", ".join(f"({t[0]:.5f}, {t[1]:.5f})" for t in uvs)}] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </Prato/Material>
    }}

    def Material "Material"
    {{
        token outputs:surface.connect = </Prato/Material/Shader.outputs:surface>

        def Shader "Shader"
        {{
            uniform token info:id = "UsdPreviewSurface"
            color3f inputs:diffuseColor.connect = </Prato/Material/Textura.outputs:rgb>
            float inputs:roughness = 0.45
            float inputs:metallic = 0
            token outputs:surface
        }}

        def Shader "Leitor"
        {{
            uniform token info:id = "UsdPrimvarReader_float2"
            token inputs:varname = "st"
            float2 outputs:result
        }}

        def Shader "Textura"
        {{
            uniform token info:id = "UsdUVTexture"
            asset inputs:file = @prato.jpg@
            float2 inputs:st.connect = </Prato/Material/Leitor.outputs:result>
            token inputs:wrapS = "clamp"
            token inputs:wrapT = "clamp"
            float3 outputs:rgb
        }}
    }}
}}
"""


def zip_stored(arquivos):
    """Zip sem compressão, com cada arquivo alinhado a 64 bytes (exigido pelo USDZ)."""
    saida = io.BytesIO()
    central = []
    for nome, dados in arquivos:
        nome_b = nome.encode("utf-8")
        pos_local = saida.tell()
        crc = zlib.crc32(dados) & 0xFFFFFFFF
        # campo extra para alinhar o início dos dados a 64 bytes
        cabecalho = pos_local + 30 + len(nome_b)
        extra_len = (64 - (cabecalho % 64)) % 64
        if 0 < extra_len < 4:
            extra_len += 64
        extra = b""
        if extra_len:
            extra = struct.pack("<HH", 0xD935, extra_len - 4) + b"\x00" * (extra_len - 4)
        saida.write(struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, 0, 0, 0x21, crc,
                                len(dados), len(dados), len(nome_b), len(extra)))
        saida.write(nome_b)
        saida.write(extra)
        saida.write(dados)
        central.append((nome_b, crc, len(dados), pos_local))
    inicio_central = saida.tell()
    for nome_b, crc, tam, pos_local in central:
        saida.write(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, 0, 0, 0x21, crc,
                                tam, tam, len(nome_b), 0, 0, 0, 0, 0, pos_local))
        saida.write(nome_b)
    fim_central = saida.tell()
    saida.write(struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(central), len(central),
                            fim_central - inicio_central, inicio_central, 0))
    return saida.getvalue()


usdz = zip_stored([("prato.usda", usda.encode("utf-8")), ("prato.jpg", textura_bytes)])
with open("prato.usdz", "wb") as f:
    f.write(usdz)
print(f"prato.usdz: {len(usdz)} bytes")
