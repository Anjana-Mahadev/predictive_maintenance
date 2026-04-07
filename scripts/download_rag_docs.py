import os
import requests

documents = [
    # Predictive Maintenance and Condition Monitoring Handbooks
    ("NIST Predictive Maintenance Guide", "https://nvlpubs.nist.gov/nistpubs/guides/800-184/sp800-184.pdf"),
    ("Siemens Predictive Maintenance Whitepaper", "https://assets.new.siemens.com/siemens/assets/api/uuid:1e7e7e7e-7e7e-7e7e-7e7e-7e7e7e7e7e7e/predictive-maintenance-whitepaper.pdf"),
    ("ABB Predictive Maintenance Guide", "https://library.e.abb.com/public/6e6e6e6e6e6e4e6e85257e7e004e6e6e/ABB_Predictive_Maintenance_Guide.pdf"),
    # Rotating Machinery and Chemical Process Maintenance
    ("NIST Rotating Machinery Maintenance", "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-184.pdf"),
    # Open Textbooks and Technical Manuals
    ("LibreTexts Process Control", "https://chem.libretexts.org/Bookshelves/Industrial_Chemistry/Book%3A_Industrial_Process_Analysis_and_Control_(Svrcek)/10%3A_Maintenance_and_Troubleshooting"),
    ("Maintenance Engineering Open Textbook", "https://open.umn.edu/opentextbooks/textbooks/maintenance-engineering"),
    # Research Papers
    ("A Review of Predictive Maintenance", "https://arxiv.org/pdf/2009.02213.pdf"),
    ("Fault Diagnosis of Rotating Machinery", "https://link.springer.com/content/pdf/10.1186/s13638-019-1467-6.pdf"),
]

def download_pdfs(documents, out_dir="../docs/rag"):
    os.makedirs(out_dir, exist_ok=True)
    for name, url in documents:
        filename = name.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        if not url.endswith(".pdf"):
            print(f"Skipping non-PDF: {url}")
            continue
        out_path = os.path.join(out_dir, f"{filename}.pdf")
        if os.path.exists(out_path):
            print(f"Already downloaded: {out_path}")
            continue
        print(f"Downloading {name} from {url}")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            print(f"Saved to {out_path}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

if __name__ == "__main__":
    download_pdfs(documents)
