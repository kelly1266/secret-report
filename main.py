import subprocess
import requests
import base64
import json
import pandas as pd
from requests.auth import HTTPBasicAuth
import config


def injectToken(uri):
    username = config.azure_username
    token = config.azure_token
    replacementStr = f'username:{token}'
    return uri.replace(username, replacementStr, 1)


def runTrufflehog(uri):
    print('Running Trufflehog')
    trufflehogExePath = config.trufflehogExePath
    subprocess.run([trufflehogExePath, 'git', '--json', uri, '>>', 'placeholder.txt'], shell=True)


def getProjectsList(response):
    projects = []
    for project in response.json()["value"]:
        projects.append(project["id"])
    return projects


def getReposList(response):
    repos = []
    for repo in response.json()["value"]:
        # what field holds a uri that trufflehog can use?
        repos.append(injectToken(repo["remoteUrl"]))
    return repos


azure_token = config.azure_token
organization = config.azure_organization

# Create authorization header
authorization = str(base64.b64encode(bytes(':'+azure_token, 'ascii')), 'ascii')
headers = {
    'Accept': 'application/json',
    'Authorization': 'Basic ' + authorization
}

# Get a list of projects
projectsResponse = requests.get(
    url=f"https://dev.azure.com/{organization}/_apis/projects?api-version=6.0",
    headers=headers
)
projectIDs = getProjectsList(projectsResponse)

# Cycle through all of the projects and get all of the repo links
reposList = []
for project in projectIDs:
    reposResponse = requests.get(
        url=f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories?api-version=4.1",
        headers=headers
    )
    reposList.extend(getReposList(reposResponse))

# Run Trufflehog
for repo in reposList:
    print(repo)
    runTrufflehog(repo)


# Add results to a csv
with open(r"./placeholder.txt") as f:
    data = f.readlines()
processed_data = [json.loads(line) for line in data]
df = pd.DataFrame(processed_data)
df.to_csv(r"./out_data.csv")