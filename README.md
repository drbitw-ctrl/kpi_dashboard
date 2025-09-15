# KPI Dashboard (Streamlit)

A web-based dashboard for visualizing team and individual KPIs from Excel or CSV.

## How to use on GitHub Codespaces or Streamlit Cloud

### Option 1: Run on [Streamlit Cloud](https://share.streamlit.io)
1. Fork this repository to your GitHub account.
2. Go to https://share.streamlit.io and deploy directly from your repo.
3. Open the app in your browser, upload your Excel file, and explore results.

### Option 2: Run in GitHub Codespaces (browser-based dev)
1. Create a Codespace from this repository.
2. In terminal, run:
```bash
pip install -r requirements.txt
streamlit run streamlit_kpi_app.py --server.headless true --server.enableCORS false
