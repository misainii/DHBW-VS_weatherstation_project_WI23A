import math
import pytest

from app.utils import haversine_km, validate_latitude, validate_longitude


def test_haversine_zero_distance():
    assert haversine_km(49.0, 10.0, 49.0, 10.0) == 0


def test_haversine_reasonable_value():
    distance = haversine_km(49.4521, 11.0767, 49.4771, 10.9887)
    assert math.isclose(distance, 6.98, rel_tol=0.1)


@pytest.mark.parametrize("value", [-90, 0, 90])
def test_validate_latitude_valid(value):
    validate_latitude(value)


@pytest.mark.parametrize("value", [-91, 91])
def test_validate_latitude_invalid(value):
    with pytest.raises(ValueError):
        validate_latitude(value)


@pytest.mark.parametrize("value", [-180, 0, 180])
def test_validate_longitude_valid(value):
    validate_longitude(value)


@pytest.mark.parametrize("value", [-181, 181])
def test_validate_longitude_invalid(value):
    with pytest.raises(ValueError):
        validate_longitude(value)
