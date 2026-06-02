import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
LEGACY_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GEOLOCATION_URL = "https://www.googleapis.com/geolocation/v1/geolocate"
DEFAULT_LOCATION = {
    "latitude": -3.7319,
    "longitude": -38.5267,
    "label": "Fortaleza/CE (padrao)",
}


def load_env(path=".env"):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def post_json(url, payload, headers=None, timeout=20):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Erro de conexao: {error.reason}") from error


def get_json(url, params, timeout=20):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full_url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Erro de conexao: {error.reason}") from error


def get_current_location(api_key):
    lat = os.getenv("USER_LATITUDE")
    lng = os.getenv("USER_LONGITUDE")
    if lat and lng:
        return {
            "latitude": float(lat),
            "longitude": float(lng),
            "label": "USER_LATITUDE/USER_LONGITUDE do .env",
        }

    try:
        response = post_json(
            f"{GEOLOCATION_URL}?key={api_key}",
            {"considerIp": True},
        )
        location = response["location"]
        return {
            "latitude": location["lat"],
            "longitude": location["lng"],
            "label": "Google Geolocation API",
        }
    except Exception as error:
        print(f"Nao foi possivel detectar sua localizacao automaticamente: {error}")
        print("Usando localizacao padrao. Para mudar, adicione USER_LATITUDE e USER_LONGITUDE no .env.")
        return DEFAULT_LOCATION


def normalize_radius(value):
    text = value.strip().lower().replace(",", ".")
    if text.endswith("km"):
        return float(text[:-2].strip()) * 1000
    if text.endswith("m"):
        return float(text[:-1].strip())

    number = float(text)
    return number * 1000 if number <= 50 else number


def distance_meters(origin, destination):
    earth_radius_meters = 6371000
    lat1 = math.radians(origin["latitude"])
    lat2 = math.radians(destination["latitude"])
    delta_lat = math.radians(destination["latitude"] - origin["latitude"])
    delta_lng = math.radians(destination["longitude"] - origin["longitude"])

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_meters * c


def search_restaurants(api_key, location, restaurant_type, radius_meters):
    try:
        return search_restaurants_new_api(api_key, location, restaurant_type, radius_meters)
    except RuntimeError as error:
        print(f"Falha na Places API (New): {error}")
        print("Tentando fallback pela Places API antiga...")
        return search_restaurants_legacy(api_key, location, restaurant_type, radius_meters)


def search_restaurants_new_api(api_key, location, restaurant_type, radius_meters):
    payload = {
        "textQuery": f"{restaurant_type} restaurant" if restaurant_type else "restaurant",
        "includedType": "restaurant",
        "strictTypeFiltering": True,
        "maxResultCount": 10,
        "rankPreference": "DISTANCE",
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                },
                "radius": radius_meters,
            }
        },
    }

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.rating,"
            "places.userRatingCount,"
            "places.primaryTypeDisplayName"
        ),
    }

    results = post_json(PLACES_URL, payload, headers=headers)
    filtered_places = []

    for place in results.get("places", []):
        place_location = place.get("location")
        if not place_location:
            continue

        distance = distance_meters(location, place_location)
        if distance <= radius_meters:
            place["distanceMeters"] = distance
            filtered_places.append(place)

    results["places"] = sorted(filtered_places, key=lambda place: place["distanceMeters"])
    return results


def search_restaurants_legacy(api_key, location, restaurant_type, radius_meters):
    query = f"{restaurant_type} restaurant" if restaurant_type else "restaurant"
    results = get_json(
        LEGACY_TEXT_SEARCH_URL,
        {
            "query": query,
            "location": f"{location['latitude']},{location['longitude']}",
            "radius": int(radius_meters),
            "type": "restaurant",
            "key": api_key,
        },
    )

    status = results.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        raise RuntimeError(f"{status}: {results.get('error_message', 'sem mensagem')}")

    places = []
    for place in results.get("results", []):
        geometry_location = place.get("geometry", {}).get("location")
        if not geometry_location:
            continue

        place_location = {
            "latitude": geometry_location["lat"],
            "longitude": geometry_location["lng"],
        }
        distance = distance_meters(location, place_location)
        if distance > radius_meters:
            continue

        places.append(
            {
                "id": place.get("place_id"),
                "displayName": {"text": place.get("name", "Sem nome")},
                "formattedAddress": place.get("formatted_address", "Endereco nao informado"),
                "location": place_location,
                "rating": place.get("rating", "sem nota"),
                "userRatingCount": place.get("user_ratings_total", 0),
                "distanceMeters": distance,
            }
        )

    return {"places": sorted(places, key=lambda place: place["distanceMeters"])}


def print_results(results):
    places = results.get("places", [])
    if not places:
        print("\nNenhum restaurante encontrado nesse raio.")
        return

    print(f"\nRestaurantes encontrados: {len(places)}\n")
    for index, place in enumerate(places, start=1):
        name = place.get("displayName", {}).get("text", "Sem nome")
        address = place.get("formattedAddress", "Endereco nao informado")
        rating = place.get("rating", "sem nota")
        total = place.get("userRatingCount", 0)
        location = place.get("location", {})

        print(f"{index}. {name}")
        print(f"   Endereco: {address}")
        print(f"   Nota: {rating} ({total} avaliacoes)")
        if "latitude" in location and "longitude" in location:
            print(f"   Localizacao: {location['latitude']}, {location['longitude']}")
        if "distanceMeters" in place:
            print(f"   Distancia aproximada: {place['distanceMeters']:.0f} m")
        print()


def main():
    load_env()
    api_key = os.getenv("API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("API_KEY nao encontrada no .env.")
        sys.exit(1)

    restaurant_type = input("Qual tipo de restaurante voce quer procurar? ").strip()
    radius_input = input("Qual raio de distancia? Ex: 2km, 500m ou 5: ").strip()

    try:
        radius_meters = normalize_radius(radius_input)
    except ValueError:
        print("Raio invalido. Use algo como 2km, 500m ou 5.")
        sys.exit(1)

    location = get_current_location(api_key)
    print(
        "\nBuscando restaurantes perto de "
        f"{location['latitude']}, {location['longitude']} ({location['label']}) "
        f"em um raio de {radius_meters:.0f} metros..."
    )

    try:
        results = search_restaurants(api_key, location, restaurant_type, radius_meters)
    except Exception as error:
        print(f"Erro ao buscar restaurantes: {error}")
        sys.exit(1)

    print_results(results)


if __name__ == "__main__":
    main()
