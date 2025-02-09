import requests
import matplotlib.pyplot as plt
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib

# Your custom theme settings
jared_theme = {
    "axes.grid": False,
    "grid.linestyle": "-",
    "grid.color": "black",
    "legend.framealpha": 1,
    "legend.facecolor": "white",
    "legend.shadow": True,
    "legend.fontsize": 14,
    "legend.title_fontsize": 16,
    "xtick.labelsize": 11,
    "ytick.labelsize": 14,
    "axes.labelsize": 14,
    "axes.titlesize": 20,
    "figure.dpi": 120,
    "axes.facecolor": "white",
    "figure.figsize": (10, 5.5),
}

matplotlib.rcParams.update(jared_theme)

# URL of the Statista page
url = "https://www.statista.com/statistics/1424043/us-states-sales-tax-on-period-products/"

# Headers to mimic a real browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Fetch the page content
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")

    # Locate the table
    table = soup.find("table", {"id": "statTableHTML"})

    if table:
        data = []
        rows = table.find_all("tr")[1:]  # Skip the header row

        for row in rows:
            cols = row.find_all("td")
            state = cols[0].text.strip()
            tax_rate = float(cols[1].text.strip().replace("%", ""))  # Remove % symbol and convert to float

            # Override Texas' value to 6.25%
            if state == "Texas":
                tax_rate = 6.25

            # Add positive tax rates to data
            if tax_rate > 0:
                data.append((state, tax_rate))

        # Convert the data into a DataFrame for easier plotting
        df = pd.DataFrame(data, columns=["State", "Sales Tax"])

        # Sort the data by sales tax in descending order
        df = df.sort_values(by="Sales Tax", ascending=False)

        # Plotting the bar graph
        plt.figure(figsize=(10, 6))
        bars = plt.barh(df["State"], df["Sales Tax"], color='#101311')  # Dark color for the bars

        # Add value annotations on the bars
        for bar, state in zip(bars, df["State"]):
            label_color = 'red' if state == "Texas" else 'blue'  # Red for Texas, blue for others
            plt.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f'{bar.get_width():.2f}%',
                     va='center', ha='left', color=label_color, fontweight='bold')

        plt.xlabel("Sales Tax")
        plt.title("Period Taxation by State (2024)")
        plt.gca().invert_yaxis()
        plt.xlim(0,7.5)
        plt.xticks([])

        # Save the plot
        plt.tight_layout()
        plt.savefig("sales_tax_on_period_products.png")  # Save the plot as PNG

        # Show the plot
        plt.show()

    else:
        print("Table not found. The content might be hidden behind JavaScript.")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
