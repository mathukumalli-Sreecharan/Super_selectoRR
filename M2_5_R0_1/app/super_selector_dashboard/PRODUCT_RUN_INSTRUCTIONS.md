# Run the IPL pressure analytics product

Open PowerShell in `M2_5_R0_1\app\super_selector_dashboard` and run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app directly validates and reads the bundled source archive. The first load may take about a minute while it builds the pressure dataset and exports. Select one of the 14 research views in the sidebar. Generated CSV/JSON files are under `data\exports`.
