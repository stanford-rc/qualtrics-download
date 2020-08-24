#!/usr/bin/env python

# Download qualtrics data programatically
# see https://github.com/stanford-rc/qualtrics-download

import argparse
import io
import os
import requests
import sys
from time import sleep
import zipfile


def get_parser():

    parser = argparse.ArgumentParser(
        description="Qualtrics Downloader",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--data-center",
        dest="data_center",
        help="The data center to download from. Defaults to ca1.",
        choices=["sjc1", "iad1", "ca1", "fra1", "syd1", "gov1"],
        default="ca1",
        type=str,
    )

    parser.add_argument(
        "--format",
        dest="fmt",
        default="csv",
        choices=["csv", "tsv", "xml"],
        help="The export format. One of csv, tsv, or xml.",
        type=str,
    )

    parser.add_argument(
        "--survey-id",
        dest="survey_id",
        help="The survey ID you want to download.",
        type=str,
    )

    parser.add_argument(
        "--output-directory",
        "-o",
        dest="output_dir",
        help="Output directory to download data. Defaults to present working directory.",
        default=os.getcwd(),
    )

    parser.add_argument(
        "--api-token",
        dest="api_token",
        help="The Qualtrics API token. You can (and should) also export this to the environment as QUALTRICS_API_TOKEN",
        default=os.environ.get("QUALTRICS_API_TOKEN"),
    )

    return parser


def do_request(url, api_token, data=None, kind="POST", stream=False):
    """make a request to the Qualtrics API
    """
    headers = {"x-api-token": api_token, "Content-Type": "application/json"}
    print(f"{kind} {url}")
    response = requests.request(kind, url, json=data, headers=headers, stream=stream)
    if response.status_code not in [201, 200]:
        sys.exit(f"Error with request {url}: {response.status_code}, {response.reason}")
    return response


def main():

    parser = get_parser()

    # We capture all primary arguments, and take secondary to pass on
    args, options = parser.parse_known_args()

    # Ensure that the survey id is provided, along with API token
    if not args.survey_id:
        sys.exit("Please provide a Qualtrics survey id to export with --survey-id")
    if not args.api_token:
        sys.exit(
            "Please provide a Qualtrics API token in the environment (QUALTRICS_API_TOKEN) or with --api-token"
        )

    # Ensure output folder exists
    outdir = os.path.abspath(args.output_dir)
    if not os.path.exists(outdir):
        sys.exit(f"Output directory {outdir} does not exist.")

    # trigger creation of export files
    baseUrl = "https://{0}.qualtrics.com/API/v3/responseexports/".format(
        args.data_center
    )

    data = {
        "surveyId": args.survey_id,
        "format": args.fmt,
    }
    response = do_request(baseUrl, args.api_token, data).json()

    # get status of export file
    progressId = response.get("result", {}).get("id")

    # Cut out early if no progress id
    if not progressId:
        sys.exit(f"Cannot get progress id in response {response}.")

    # Wait for download to be ready, increase delay in checking
    status = "notcomplete"
    url = "%s%s" % (baseUrl, progressId)
    pause = 2  # pause in seconds
    while status not in ["complete", "error"]:
        response = do_request(url, args.api_token, kind="GET").json()
        status = response.get("result", {}).get("status")
        percent = response.get("result", {}).get("percentComplete")
        print(f"Download is {percent}% complete")
        if status != "complete":
            sleep(pause)
            pause = pause * 2

    # Download file (if you have issues here, we can update to stream in chunks)
    url = "%s/file" % url
    response = do_request(url, args.api_token, kind="GET", stream=True)

    # Unzipping to output directory
    print(f"Unzipping to {outdir}...")
    zipfile.ZipFile(io.BytesIO(response.content)).extractall(outdir)
    print("Complete!")
    print("\n".join(os.listdir(outdir)))


if __name__ == "__main__":
    main()
