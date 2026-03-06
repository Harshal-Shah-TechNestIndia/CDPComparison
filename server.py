# server.py

import os
import json
from urllib.parse import urlparse
from flask import Flask, request, jsonify, abort, render_template

from app2 import process,extract_section_based_qas,summarize  # <-- your real process() function

UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "."   # JSON files saved in project root

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

import asyncio


# ----------------------------------------------------------
# UI ROUTES
# ----------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")   # homepage

@app.route("/compare")
def compare():
    return render_template("compare.html")  # comparison UI

# ----------------------------------------------------------
# 1) Upload PDF
# ----------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    files = request.files.getlist("documents")
    if not files:
        return jsonify({"error": "No files received"}), 400

    saved = []
    for f in files:
        name = f.filename
        if not name:
            continue
        dest = os.path.join(app.config["UPLOAD_FOLDER"], name)
        f.save(dest)
        saved.append(name)

    return jsonify({"status": "success", "files": saved})


# ----------------------------------------------------------
# 2) Process PDF (URL or local)
# ----------------------------------------------------------
@app.route("/process", methods=["POST"])
def process_pdf():
    data = request.get_json(silent=True) or {}

    company_name = data.get("company_name")
    source = data.get("source")

    if not company_name or not source:
        return jsonify({"error": "company_name and source are required"}), 400

    parsed = urlparse(source)

    # remote URL
    if parsed.scheme in ("http", "https"):
        pdf_source = source
    else:
        # local upload
        path = os.path.join(UPLOAD_FOLDER, source)
        if not os.path.isfile(path):
            abort(404, f"File not found: {source}")
        pdf_source = path

    # ---- call the pipeline from app2, but be tolerant about its return shape ----
    try:
        result = process(company_name, pdf_source)  # may be (fname, err) OR str OR None
    except Exception as e:
        # hard failure during processing
        return jsonify({"error": f"processing raised: {e}"}), 500

    output_file = None
    err = None

    # Case A: tuple (output_file, err)
    if isinstance(result, tuple):
        if len(result) == 2:
            output_file, err = result
        else:
            # unexpected tuple length; treat as error
            err = f"Unexpected return tuple from process(): {result}"
    # Case B: simple string: just the filename
    elif isinstance(result, str):
        output_file = result
    # Case C: None or unknown: try to infer the expected filename
    elif result is None:
        # infer a safe file name like output_<company>.json (RESULTS_FOLDER defaults to ".")
        safe_company = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in company_name.strip())
        guessed = f"output_{safe_company}.json"
        if os.path.isfile(os.path.join(RESULTS_FOLDER, guessed)):
            output_file = guessed
        else:
            err = "process() returned no result and expected output file was not found."

    # Return any error reported/resolved above
    if err:
        return jsonify({"error": err}), 500

    if not output_file:
        return jsonify({"error": "No output file produced"}), 500

    return jsonify({
        "status": "success",
        "output_json": output_file
    })

# ----------------------------------------------------------
# 3) List generated JSON files
# ----------------------------------------------------------
@app.route("/list_json", methods=["GET"])
def list_json():
    files = [f for f in os.listdir(RESULTS_FOLDER) if f.startswith("output_") and f.endswith(".json")]
    return jsonify({"files": files})


# ----------------------------------------------------------
# 4) Fetch JSON content for UI
# ----------------------------------------------------------
@app.route("/json", methods=["GET"])
def fetch_json():
    filename = request.args.get("file")
    if not filename:
        return jsonify({"error": "file parameter missing"}), 400

    if not filename.startswith("output_") or not filename.endswith(".json"):
        return jsonify({"error": "invalid filename"}), 400

    filepath = os.path.join(RESULTS_FOLDER, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "file not found"}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)


@app.route("/common_sections", methods=["GET"])
def common_sections():
    file1 = request.args.get("file1")
    file2 = request.args.get("file2")

    if not file1 or not file2:
        return jsonify({"error": "file1 and file2 are required"}), 400

    # Validate names
    for f in (file1, file2):
        if not f.startswith("output_") or not f.endswith(".json"):
            return jsonify({"error": f"invalid filename: {f}"}), 400
        if not os.path.isfile(f):
            return jsonify({"error": f"file not found: {f}"}), 404

    # Load JSON files
    with open(file1, "r", encoding="utf-8") as fh:
        js1 = json.load(fh)
    with open(file2, "r", encoding="utf-8") as fh:
        js2 = json.load(fh)

    # Extract sections: note your JSON uses top-level numeric keys "2", "3", etc.
    def collect_sections(js):
        sections = set()
        for key, arr in js.items():
            if key.isdigit() and isinstance(arr, list):
                for entry in arr:
                    sec = entry.get("section", "").strip()
                    if sec:
                        sections.add(sec)
        return sections

    sec1 = collect_sections(js1)
    sec2 = collect_sections(js2)

    common = sorted(sec1.intersection(sec2), key=lambda s: [int(x) for x in s.split(".")])

    return jsonify({"common_sections": common})


@app.route("/extract_sections", methods=["GET"])
def extract_sections_endpoint():
    """
    Accepts:
      - prefix: e.g. "7"
      - file1: JSON filename
      - file2: JSON filename

    For now: returns empty string
    """

    prefix = request.args.get("prefix", "").strip()
    file1 = request.args.get("file1", "").strip()
    file2 = request.args.get("file2", "").strip()

    # Basic validation
    if not prefix or not file1 or not file2:
        return jsonify({"error": "prefix, file1, file2 are required"}), 400

    # Validate filenames
    for f in (file1, file2):
        if not f.startswith("output_") or not f.endswith(".json"):
            return jsonify({"error": f"invalid filename: {f}"}), 400
        if not os.path.isfile(f):
            return jsonify({"error": f"file not found: {f}"}), 404


    # Helper: load JSON safely
    def _load_json(path: str):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return None, f"Top-level JSON is not an object in file: {path}"
            return data, None
        except json.JSONDecodeError as e:
            return None, f"JSON decode error in {path}: {e}"
        except OSError as e:
            return None, f"OS error when reading {path}: {e}"


    # Load both files
    data1, err1 = _load_json(file1)
    if err1:
        return jsonify({"error": err1}), 400

    data2, err2 = _load_json(file2)
    if err2:
        return jsonify({"error": err2}), 400


    # merged: dict = {}
    # merged.update(data1)
    # merged.update(data2)

    print(f"prefix {prefix} file1 {file1} and file2 {file2}")

    section_headers = {
        "1": "Introduction",
        "2": "Identification, assessment of impacts, risks and opportunities",
        "3": "Disclosure of risks and opportunities",
        "4": "Governance",
        "5": "Business Strategy",
        "6": "Consolidation Approach",
        "7": "Climate Change",
        "9": "Water Security",
        "13": "Further Information & Sign Off"
    }

    try:
        result_str1 = extract_section_based_qas(data1, prefix=prefix)  # returns a single formatted string
        result_str2 = extract_section_based_qas(data2, prefix=prefix)  # returns a single formatted string
        
        merged_result_str = f"Topic of Comparison: {section_headers.get(prefix, 'Emission Control')} Data from {file1}:- \n {result_str1}\n\nData from {file2}:- \n {result_str2}"

        # print(f"Raw Data {merged_result_str}")

        summary = asyncio.run(summarize(merged_result_str))

        # print(f"Summary Data {summary}")

    except Exception as e:
        # In case the callable raises (unexpected data shape, etc.)
        return jsonify({"error": f"Failed to extract Q&A: {e}"}), 500

    # If nothing matched, keep the contract and return empty string as "result"
    # (Your callable already returns "" if nothing is appended; if not, we normalize it.)
    if not isinstance(summary, str):
        summary = ""

    return jsonify({"result": summary})

# ----------------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------------
@app.route("/health")
def health():
    return {"status": "ok"}


# ----------------------------------------------------------
# RUN SERVER
# ----------------------------------------------------------
if __name__ == "__main__":
    print("Server running at http://127.0.0.1:5000")
    app.run(host = "0.0.0.0", port=5000, debug=True)