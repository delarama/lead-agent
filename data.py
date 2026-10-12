"""Fake data for the lead negotiation agent. No database is needed."""

# Four cars that private sellers have listed.
LISTINGS = {
    "L1": {"id": "L1", "seller_name": "Sam", "year": 2019, "make": "Honda",
           "model": "Civic", "mileage_km": 82000, "listed_price": 18500},
    "L2": {"id": "L2", "seller_name": "Priya", "year": 2018, "make": "Toyota",
           "model": "RAV4", "mileage_km": 110000, "listed_price": 24000},
    "L3": {"id": "L3", "seller_name": "Marco", "year": 2017, "make": "Ford",
           "model": "F-150", "mileage_km": 140000, "listed_price": 27500},
    "L4": {"id": "L4", "seller_name": "Lena", "year": 2020, "make": "Mazda",
           "model": "3", "mileage_km": 60000, "listed_price": 21000},
}

# The business rule: the dealer pays at most 90% of the listed price.
# In a real product this number would come from the pricing models.
LIMIT_RATE = 0.90


def price_limit(listing_id: str) -> int:
    """The highest price the agent may agree to for this listing."""
    return round(LISTINGS[listing_id]["listed_price"] * LIMIT_RATE)


# The dealer's free appointment times this week.
SLOTS = ["Tuesday 10:00", "Tuesday 14:00", "Wednesday 11:00", "Thursday 16:00"]
