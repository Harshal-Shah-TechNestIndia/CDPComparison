import json
from py2pdf_extraction import *
import sys

def extractqas(reader: PdfReader,company_name: str, pdf_source: str) -> dict:
    # Dictionary to store everything
    results = {}   # { page_num: [ {section, question, answer}, ... ] }

    # Process extract pdf pagewise 
    for page_num, page_text in iter_page_text(reader):
        if not page_text.strip():
            continue

        page_entries = []  # store Q/A entries for this page

        for section, question, answer in extract_qas_from_page(page_text):
            entry = {
                "section": section,
                "question": question,
                "answer": answer or ""
            }

            page_entries.append(entry)
        
        if page_entries:
            results["company_name"] = company_name
            results["pdf_source"] = pdf_source
            results[page_num] = page_entries


    return results

def save_json(results, company_name):
    # ---- Save dictionary into JSON ----
    try:
        output_filename = f"output_{company_name}.json"

        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        print(f"Saved extraction to {output_filename}")
    except Exception as e:
        print("Extraction could not be saved")
        print(e)

def load_pdf(pdf_source):
    try:
        reader = load_pdf_reader(pdf_source)
        return reader
    except Exception as e:
        print(f"Failed to open PDF: {e}", file=sys.stderr)
        sys.exit(1)

def process(company_name, pdf_source):
    # Load the PDF into memory
    reader = load_pdf(pdf_source)

    results = extractqas(reader, company_name, pdf_source)
    
    if len(results) != 0:
        save_json(results, company_name)
    else:
        print("Could not save")
        # print(results)

def extract_section_based_qas(data, prefix = "7"):
    """
    Return all question–answer pairs where:
    - section starts with '7.'
    - answer is NOT blank
    - answer does NOT contain long dot filler like '......'
    """
    prefix = prefix + "."
    results = []

    for _, entries in data.items():
        if isinstance(entries, list):
            for item in entries:
                section = item.get("section", "")
                question = item.get("question", "").strip()
                answer = item.get("answer", "").strip()

                if not section.startswith(prefix):
                    continue

                # Filter: skip blank or dot‑filled answers
                if answer == "" or ("...." in answer):   # 4+ dots = filler
                    continue

                results.append({
                    "section": section,
                    "question": question,
                    "answer": answer
                })
                
                # result = (
                #     f"---\n"
                #     f"Section: {section}\n"
                #     f"Question: {question}\n"
                #     f"Answer: {answer}"
                # )
                # results.append(result)

    # results = [f"---\n"f"Section: {result["section"]}\nQuestion: {result["question"]}\nAnswer: {result["answer"]}\n\n" for result in results[-15:]]
    
    results = [
        f"---\n"
        f"Section: {result['section']}\n"
        f"Question: {result['question']}\n"
        f"Answer: {result['answer']}\n\n"
        for result in results[:]
    ]

    return "\n\n".join(results)


from agents import SummarizingAgent

async def summarize(text):
    agent = SummarizingAgent()
    summary = await agent.summarize_text(text)
    return summary


# if __name__ == "__main__":
#     # You can change this to a local file path if preferred.
#     pdf_source1 = "https://corporate.thermofisher.com/content/dam/tfcorpsite/documents/corporate-social-responsibility/Thermo-Fisher-Scientific-Inc-2024-FINAL-CDP-REPORT.pdf"
#     company_name1 = "Thomas_Fisher"

#     pdf_source2 = "https://www.merck.com/wp-content/uploads/sites/124/2025/07/2024-CDP-Disclosure.pdf"
#     company_name2 = "Merck"

#     process(company_name1,pdf_source1)
#     process(company_name2,pdf_source2)


# input_path = "output_corporate.json"

# with open(input_path, "r", encoding="utf-8") as f:
#     data = json.load(f)

# # Extract all 7.* Q&A
# qas_7 = extract_section_based_qas(data)

# print(f"Found {len(qas_7)} Q&A entries starting with section '7.'")

# print(qas_7)
# # Preview a few entries
# for qa in qas_7[:5]:
#     print("\n---")
#     print("Section:", qa["section"])
#     print("Question:", qa["question"])
#     print("Answer:", qa["answer"])




# text = """
# Large language models are capable of performing a wide range of tasks,
# including summarization, reasoning, and coding assistance. They are
# increasingly used in enterprise systems to automate document analysis.
# """


# import asyncio
# print(asyncio.run(summarize(text)))