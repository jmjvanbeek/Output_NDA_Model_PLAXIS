import requests
import pandas as pd
import matplotlib.pyplot as plt

BASE_URL = "https://barkasapi.delftschestudentenbond.nl"
AUTH = ("scorpios", "GroeneDingenZijnMooi")


def fetch(path: str) -> dict | list:
    resp = requests.get(f"{BASE_URL}{path}", auth=AUTH)
    resp.raise_for_status()
    return resp.json()


def build_invoices_df(details: list) -> pd.DataFrame:
    rows = []

    for inv in details:
        rows.append({
            "id": inv["id"],
            "date": inv["date"],
            "total": inv["total"],
            "is_paid": inv["is_paid"],
            "synced": inv["synced"],
        })

    df = pd.DataFrame(rows)

    # ✅ FIX: timezone verwijderen (crasht anders later)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

    return df


def main():
    # ✅ 1. invoices ophalen
    invoice_list = fetch("/invoices/")
    print(f"Totaal aantal invoices: {len(invoice_list)}")
    print(invoice_list[1])

    # ✅ 2. details ophalen
    details = [fetch(f"/invoices/{inv['id']}/") for inv in invoice_list]

    # ✅ 3. dataframe maken
    invoices_df = build_invoices_df(details)

    # ✅ 4. collegejaren (met juiste datatype!)
    jaar_ranges = [
        ("Jaar 1", pd.Timestamp("2019-08-18"), pd.Timestamp("2020-08-14")),
        ("Jaar 2", pd.Timestamp("2020-08-14"), pd.Timestamp("2021-08-15")),
        ("Jaar 3", pd.Timestamp("2021-08-15"), pd.Timestamp("2022-08-21")),
        ("Jaar 4", pd.Timestamp("2022-08-21"), pd.Timestamp("2023-08-13")),
        ("Jaar 5", pd.Timestamp("2023-08-13"), pd.Timestamp("2024-08-18")),
        ("Jaar 6", pd.Timestamp("2024-08-18"), pd.Timestamp("2025-08-17")),
        ("Jaar 7", pd.Timestamp("2025-08-17"), pd.Timestamp("2026-08-10")),
    ]

    # ✅ 5. functie voor toewijzen collegejaar
    def bepaal_jaar(datum):
        for naam, start, eind in jaar_ranges:
            if start <= datum < eind:
                return naam
        return "Onbekend"
    print('done')
    # ✅ 6. kolom toevoegen
    invoices_df["collegejaar"] = invoices_df["date"].apply(bepaal_jaar)

    # ✅ (optioneel) filter onbekend eruit
    invoices_df = invoices_df[invoices_df["collegejaar"] != "Onbekend"]

    # ✅ 7. groeperen en optellen
    jaar_overzicht = (
        invoices_df
        .groupby("collegejaar")["total"]
        .sum()
        .reindex([j[0] for j in jaar_ranges])  # juiste volgorde
    )

    print("\n--- Uitgaven per collegejaar ---")
    print(jaar_overzicht)

    # ✅ 8. grafiek
    plt.figure(figsize=(10, 5))
    jaar_overzicht.plot(kind="bar", color="skyblue")

    plt.title("Totale uitgaven per collegejaar")
    plt.xlabel("Collegejaar")
    plt.ylabel("Totale uitgaven (€)")
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()