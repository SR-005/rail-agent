def availability(route_details: str) -> str:
    print(f"Searching train availability for: {route_details}")
    return "Train 12617 (Mangala Exp) has 42 seats available in SL class."


def trackstatus(trainnumber: str) -> str:
    print(f"Monitoring train #{trainnumber}...")
    return (
        f"I have started the background agent to watch train {trainnumber}. "
        "I will notify you the moment a seat opens up."
    )
