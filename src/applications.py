import os

import pandas as pd
import json

app_folder = "HUPD/"
range_years = range(2008, 2017)

def get_app_claims(app_id)-> dict:
    for year in range_years:
        try:
            with open(f"{app_folder}{year}/{app_id}.json", "r") as f:
                return json.load(f)["claims"]
        except FileNotFoundError:
            continue
    return None

def get_app_title(app_id)-> str:
    for year in range_years:
        try:
            with open(f"{app_folder}{year}/{app_id}.json", "r") as f:
                return json.load(f)["title"]
        except FileNotFoundError:
            continue
    return None

def get_app_cpc(app_id)-> list:
    for year in range_years:
        try:
            with open(f"{app_folder}{year}/{app_id}.json", "r") as f:
                return json.load(f)["cpc_labels"]
        except FileNotFoundError:
            continue
    return None

def reset_app_list():
    """Reset the list of application IDs by scanning the HUPD folders and saving the list to a CSV file."""
    app_ids = pd.DataFrame(columns=["app_id", "year"])
    for year in range_years:
        try:
            files = pd.Series(os.listdir(f"{app_folder}{year}/"))
            files = files.str.replace(".json", "")
            #add file + year to app_ids list
            year_app_ids = files.tolist()
            app_ids = pd.concat([app_ids, pd.DataFrame({"app_id": year_app_ids, "year": year})], ignore_index=True)
        except FileNotFoundError:
            continue
    app_ids.to_csv("database/list_apps.csv", index=False)
    return app_ids


def get_app_file_path(app_id):
    for year in range_years:
        file_path = f"{app_folder}{year}/{app_id}.json"
        if os.path.exists(file_path):
            return file_path
    return None

def get_app_list():
    app_ids = []
    try:
        with open("database/list_apps.csv", "r") as f:
            df = pd.read_csv(f)
            app_ids = df["app_id"].astype(str).tolist()
            return app_ids
    except FileNotFoundError:
        pass

    #if not found, reset the list and return it
    return reset_app_list()

def get_app_decision(app_id):
    path = get_app_file_path(app_id)
    if path:
        with open(path, "r") as f:
            return json.load(f)["decision"]
    return None

def get_app_info(app_id):
    claims = get_app_claims(app_id)
    title = get_app_title(app_id)
    cpc = get_app_cpc(app_id)
    decision = get_app_decision(app_id)
    return {"claims": claims, "title": title, "cpc": cpc, "decision": decision}

if __name__ == "__main__":
    app_id = "14910804"  # Example application ID
    app_id = "14910804"
    print(get_app_claims(app_id))
    print(get_app_title(app_id))
    print(get_app_cpc(app_id))
    print(len(get_app_list()))
    print(get_app_decision(app_id))
    reset_app_list()
    apps = get_app_list()
    print(len(apps))
