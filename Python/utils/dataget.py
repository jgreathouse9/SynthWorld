def get_unique_policies(file_path, sheet_name="for stata"):
    """
    Extracts states with legalized cannabis policies from an Excel file.

    Parameters:
        file_path (str): Path to the Excel file.
        sheet_name (str): Sheet name containing the policy data.

    Returns:
        list: List of state abbreviations where cannabis is legal.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df = df.drop(index=range(51, 57))  # Remove extra rows
    df = df.dropna(
        subset=["dispensary_open_date"]
    )  # Keep rows with a dispensary open date
    df = df.sort_values(by="dispensary_open_date")  # Sort by date
    df = df[["state", "st", "dispensary_open_date"]]
    df = df[~df["st"].isin(["AK", "HI"])]  # Remove AK and HI
    return df.iloc[:, 1].unique().tolist()  # Return state abbreviations


def get_treated_states(policy_url, restricted_statuses):
    """
    Fetches states with restricted abortion policies from an online dataset.

    Parameters:
        policy_url (str): URL to the policy dataset (CSV format).
        restricted_statuses (list): List of policy labels to filter.

    Returns:
        list: List of state names where abortion is banned or restricted.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(policy_url, headers=headers)
    if response.status_code == 200:
        policydf = pd.read_csv(StringIO(response.text), sep="\t")
        return policydf[policydf["Status of Abortion"].isin(restricted_statuses)][
            "State"
        ].tolist()
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return []

