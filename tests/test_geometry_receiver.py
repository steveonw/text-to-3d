"""
Tests for scripts/authoring/geometry_receiver.py

Coverage:
  - validate_primitive: shape, dimensions, position, rotation, material
  - validate_packet: piece_id, primitives list
  - receive_packet / receive_all aliases
  - GeometryError raised for all violations
  - Normalisation: floats, lowercase hex, defaults applied
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from authoring.geometry_receiver import (
    validate_primitive,
    validate_packet,
    receive_packet,
    receive_all,
    GeometryError,
    SUPPORTED_SHAPES,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _prim(shape="box", dims=None, position=None, rotation=None, material=None):
    p = {"shape": shape}
    _default_dims = {
        "box": [1, 2, 1], "cylinder": [0.5, 0.5, 2], "cone": [0.5, 1],
        "sphere": [0.5], "plane": [2, 3],
    }
    p["dimensions"] = dims if dims is not None else _default_dims.get(shape, [1, 1, 1])
    if position is not None:
        p["position"] = position
    if rotation is not None:
        p["rotation"] = rotation
    p["material"] = material if material is not None else {"color": "#aabbcc"}
    return p


def _packet(piece_id=0, primitives=None):
    return {
        "piece_id": piece_id,
        "primitives": primitives if primitives is not None else [_prim()],
    }


# ── Shape validation ───────────────────────────────────────────────────────────

def test_all_supported_shapes_accepted():
    for shape in SUPPORTED_SHAPES:
        result = validate_primitive(_prim(shape=shape))
        assert result["shape"] == shape


def test_unsupported_shape_raises():
    with pytest.raises(GeometryError, match="shape must be one of"):
        validate_primitive(_prim(shape="torus"))


def test_none_shape_raises():
    with pytest.raises(GeometryError):
        validate_primitive({"dimensions": [1, 2, 1], "material": {"color": "#aabbcc"}})


# ── Dimension validation ───────────────────────────────────────────────────────

@pytest.mark.parametrize("shape,dims", [
    ("box",      [1, 2, 1]),
    ("cylinder", [0.5, 0.5, 2]),
    ("cone",     [0.5, 1]),
    ("sphere",   [0.5]),
    ("plane",    [2, 3]),
])
def test_correct_dimension_count_accepted(shape, dims):
    result = validate_primitive(_prim(shape=shape, dims=dims))
    assert result["dimensions"] == [float(d) for d in dims]


@pytest.mark.parametrize("shape,dims", [
    ("box",      [1, 2]),          # too few
    ("cylinder", [0.5, 0.5]),      # too few
    ("cone",     [0.5, 1, 2]),     # too many
    ("sphere",   [0.5, 0.5]),      # too many
    ("plane",    [2]),             # too few
])
def test_wrong_dimension_count_raises(shape, dims):
    with pytest.raises(GeometryError, match="requires exactly"):
        validate_primitive(_prim(shape=shape, dims=dims))


def test_zero_dimension_raises():
    with pytest.raises(GeometryError, match="positive"):
        validate_primitive(_prim(shape="box", dims=[0, 2, 1]))


def test_negative_dimension_raises():
    with pytest.raises(GeometryError, match="positive"):
        validate_primitive(_prim(shape="sphere", dims=[-1]))


def test_dimensions_coerced_to_float():
    result = validate_primitive(_prim(shape="box", dims=[1, 2, 3]))
    assert all(isinstance(d, float) for d in result["dimensions"])


def test_non_numeric_dimension_raises():
    with pytest.raises(GeometryError):
        validate_primitive(_prim(shape="box", dims=["a", 2, 1]))


# ── Position / rotation validation ────────────────────────────────────────────

def test_position_defaults_to_origin():
    result = validate_primitive(_prim())
    assert result["position"] == [0.0, 0.0, 0.0]


def test_rotation_defaults_to_zero():
    result = validate_primitive(_prim())
    assert result["rotation"] == [0.0, 0.0, 0.0]


def test_position_explicit_values():
    result = validate_primitive(_prim(position=[1, 2.5, -3]))
    assert result["position"] == [1.0, 2.5, -3.0]


def test_rotation_explicit_values():
    result = validate_primitive(_prim(rotation=[0, 90, 0]))
    assert result["rotation"] == [0.0, 90.0, 0.0]


def test_position_wrong_length_raises():
    with pytest.raises(GeometryError, match="position"):
        validate_primitive(_prim(position=[1, 2]))


def test_rotation_wrong_length_raises():
    with pytest.raises(GeometryError, match="rotation"):
        validate_primitive(_prim(rotation=[0, 90]))


def test_position_non_numeric_raises():
    with pytest.raises(GeometryError, match="position"):
        validate_primitive(_prim(position=["x", 0, 0]))


# ── Material validation ────────────────────────────────────────────────────────

def test_material_required():
    p = {"shape": "box", "dimensions": [1, 2, 1]}
    with pytest.raises(GeometryError, match="material"):
        validate_primitive(p)


def test_color_required_in_material():
    with pytest.raises(GeometryError, match="color"):
        validate_primitive(_prim(material={"roughness": 0.5}))


def test_color_normalised_to_lowercase():
    result = validate_primitive(_prim(material={"color": "#AABBCC"}))
    assert result["material"]["color"] == "#aabbcc"


def test_invalid_color_format_raises():
    with pytest.raises(GeometryError, match="color"):
        validate_primitive(_prim(material={"color": "red"}))


def test_short_hex_raises():
    with pytest.raises(GeometryError, match="color"):
        validate_primitive(_prim(material={"color": "#abc"}))


def test_roughness_default():
    result = validate_primitive(_prim(material={"color": "#aabbcc"}))
    assert result["material"]["roughness"] == 0.85


def test_metalness_default():
    result = validate_primitive(_prim(material={"color": "#aabbcc"}))
    assert result["material"]["metalness"] == 0.05


def test_roughness_explicit():
    result = validate_primitive(_prim(material={"color": "#aabbcc", "roughness": 0.3}))
    assert result["material"]["roughness"] == 0.3


def test_metalness_explicit():
    result = validate_primitive(_prim(material={"color": "#aabbcc", "metalness": 0.9}))
    assert result["material"]["metalness"] == 0.9


def test_roughness_out_of_range_raises():
    with pytest.raises(GeometryError, match="roughness"):
        validate_primitive(_prim(material={"color": "#aabbcc", "roughness": 1.5}))


def test_metalness_out_of_range_raises():
    with pytest.raises(GeometryError, match="metalness"):
        validate_primitive(_prim(material={"color": "#aabbcc", "metalness": -0.1}))


def test_emissive_accepted():
    result = validate_primitive(_prim(material={
        "color": "#aabbcc", "emissive": "#ff6600"
    }))
    assert result["material"]["emissive"] == "#ff6600"
    assert result["material"]["emissive_intensity"] == 0.5


def test_emissive_intensity_explicit():
    result = validate_primitive(_prim(material={
        "color": "#aabbcc", "emissive": "#ff0000", "emissive_intensity": 0.8
    }))
    assert result["material"]["emissive_intensity"] == 0.8


def test_emissive_intensity_negative_raises():
    with pytest.raises(GeometryError, match="emissive_intensity"):
        validate_primitive(_prim(material={
            "color": "#aabbcc", "emissive": "#ff0000", "emissive_intensity": -1
        }))


def test_emissive_invalid_hex_raises():
    with pytest.raises(GeometryError, match="color"):
        validate_primitive(_prim(material={"color": "#aabbcc", "emissive": "orange"}))


def test_emissive_absent_means_no_key():
    result = validate_primitive(_prim(material={"color": "#aabbcc"}))
    assert "emissive" not in result["material"]


def test_material_not_dict_raises():
    with pytest.raises(GeometryError, match="material"):
        validate_primitive(_prim(material="brown"))


# ── Primitive not a dict ───────────────────────────────────────────────────────

def test_primitive_not_dict_raises():
    with pytest.raises(GeometryError, match="dict"):
        validate_primitive("box")


def test_primitive_none_raises():
    with pytest.raises(GeometryError):
        validate_primitive(None)


# ── validate_packet ────────────────────────────────────────────────────────────

def test_valid_packet_round_trips():
    pkt = _packet(piece_id=5)
    result = validate_packet(pkt)
    assert result["piece_id"] == 5
    assert len(result["primitives"]) == 1


def test_packet_zero_piece_id_ok():
    result = validate_packet(_packet(piece_id=0))
    assert result["piece_id"] == 0


def test_packet_negative_piece_id_raises():
    with pytest.raises(GeometryError, match="piece_id"):
        validate_packet(_packet(piece_id=-1))


def test_packet_float_piece_id_raises():
    with pytest.raises(GeometryError, match="piece_id"):
        validate_packet(_packet(piece_id=1.5))


def test_packet_string_piece_id_raises():
    with pytest.raises(GeometryError, match="piece_id"):
        validate_packet(_packet(piece_id="seven"))


def test_packet_empty_primitives_raises():
    with pytest.raises(GeometryError, match="non-empty"):
        validate_packet(_packet(primitives=[]))


def test_packet_primitives_not_list_raises():
    with pytest.raises(GeometryError, match="non-empty"):
        validate_packet({"piece_id": 0, "primitives": None})


def test_packet_not_dict_raises():
    with pytest.raises(GeometryError, match="dict"):
        validate_packet([1, 2, 3])


def test_packet_error_includes_primitive_index():
    bad_prim = _prim(shape="sphere", dims=[-1])
    with pytest.raises(GeometryError, match=r"primitives\[0\]"):
        validate_packet(_packet(primitives=[bad_prim]))


def test_packet_multiple_primitives_all_validated():
    prims = [_prim("box"), _prim("sphere"), _prim("cone")]
    result = validate_packet(_packet(primitives=prims))
    assert len(result["primitives"]) == 3


# ── receive_packet ─────────────────────────────────────────────────────────────

def test_receive_packet_is_alias():
    pkt = _packet(piece_id=9)
    assert receive_packet(pkt) == validate_packet(pkt)


# ── receive_all ────────────────────────────────────────────────────────────────

def test_receive_all_list():
    packets = [_packet(piece_id=1), _packet(piece_id=2)]
    result = receive_all(packets)
    assert set(result.keys()) == {1, 2}
    assert result[1]["piece_id"] == 1


def test_receive_all_dict():
    packets = {1: _packet(piece_id=1), 2: _packet(piece_id=2)}
    result = receive_all(packets)
    assert set(result.keys()) == {1, 2}


def test_receive_all_empty_list():
    assert receive_all([]) == {}


def test_receive_all_not_list_or_dict_raises():
    with pytest.raises(GeometryError, match="list or dict"):
        receive_all("bad input")


def test_receive_all_stops_on_first_error():
    good = _packet(piece_id=1)
    bad = _packet(piece_id=-1)
    with pytest.raises(GeometryError):
        receive_all([good, bad])


def test_receive_all_returns_dict_keyed_by_piece_id():
    packets = [_packet(piece_id=i) for i in range(5)]
    result = receive_all(packets)
    assert list(result.keys()) == list(range(5))


# ── Full round-trip: tree and lantern ─────────────────────────────────────────

def test_tree_packet_round_trip():
    pkt = {
        "piece_id": 7,
        "primitives": [
            {
                "shape": "cylinder",
                "dimensions": [0.15, 0.15, 0.9],
                "position": [0.0, 0.45, 0.0],
                "material": {"color": "#5c3d1e", "roughness": 0.9},
            },
            {
                "shape": "cone",
                "dimensions": [0.55, 1.4],
                "position": [0.0, 1.6, 0.0],
                "material": {"color": "#2d5a27"},
            },
        ],
    }
    result = validate_packet(pkt)
    assert result["piece_id"] == 7
    assert result["primitives"][0]["shape"] == "cylinder"
    assert result["primitives"][1]["material"]["roughness"] == 0.85  # default applied


def test_lantern_with_emissive_round_trip():
    pkt = {
        "piece_id": 12,
        "primitives": [
            {
                "shape": "box",
                "dimensions": [0.3, 0.05, 0.3],
                "position": [0.0, 1.2, 0.0],
                "material": {"color": "#444444", "roughness": 0.6, "metalness": 0.4},
            },
            {
                "shape": "box",
                "dimensions": [0.22, 0.35, 0.22],
                "position": [0.0, 1.375, 0.0],
                "material": {
                    "color": "#ffdd88",
                    "roughness": 0.3,
                    "emissive": "#FFCC44",
                    "emissive_intensity": 0.8,
                },
            },
        ],
    }
    result = validate_packet(pkt)
    mat = result["primitives"][1]["material"]
    assert mat["emissive"] == "#ffcc44"   # normalised to lowercase
    assert mat["emissive_intensity"] == 0.8
