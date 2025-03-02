#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import webbrowser

# Original balance sheet data
original_data = {
    "Counterparty": ["Bank A", "Bank A", "Bank B", "Bank B", "Bank C", "Bank C"],
    "Product": ["Loans", "Deposits", "Bonds", "Borrowings", "Derivatives", "Central Bank Reserves"],
    "Amount": [500, 400, 300, 200, 150, 300]
}
df_counterparty = pd.DataFrame(original_data)

# Initial LCR metrics
original_lcr_data = {
    "Metric": ["HQLA", "Inflows", "Outflows", "Net Cash Outflows", "Liquidity Coverage Ratio (LCR) %"],
    "Value": [1300, 300, 1100, 800, 162.5]
}
df_lcr = pd.DataFrame(original_lcr_data)

# Simulation results
df_simulations = pd.DataFrame(columns=["Counterparty", "Product", "Amount", "Debit/Credit", "New LCR %", "Affected Category"])

# Simulation logic table (Product impact on LCR categories)
df_simulation_logic = pd.DataFrame({
    "Product": ["Loans", "Deposits", "Bonds", "Borrowings", "Derivatives", "Central Bank Reserves"],
    "Debit Impact on LCR": ["Increases Inflows", "Decreases Outflows", "Increases HQLA", "Decreases Inflows", "Varies", "Increases HQLA"],
    "Credit Impact on LCR": ["Decreases Inflows", "Increases Outflows", "Decreases HQLA", "Increases Inflows", "Varies", "Decreases HQLA"]
})

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
server = app.server

def create_gauge(lcr_value):
    """Creates a gauge chart for LCR percentage"""
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=lcr_value,
        title={"text": "Liquidity Coverage Ratio (LCR) %"},
        gauge={"axis": {"range": [0, 300]}, "bar": {"color": "blue"}}
    ))

# Layout
app.layout = dbc.Container([
    html.H1("Treasury Dashboard", className="text-center mb-4", style={"color": "black"}),
    
    # Instructions
    html.H4("How to Use", className="mt-3"),
    html.P("1. Select a Counterparty, Product, and Transaction Type (Debit or Credit)."),
    html.P("2. Enter an amount and click 'Apply Transaction' to see the impact on LCR."),
    html.P("3. Click 'Reset' to restore the original data."),
    html.P("4. Click 'Export Simulation' to download results as an Excel file."),

    # Table explaining impact of transactions
    html.H4("Simulation Logic", className="mt-3"),
    dash_table.DataTable(id="simulation-logic-table", data=df_simulation_logic.to_dict("records"), page_size=6),

    # User Input Section
    dbc.Row([
        dbc.Col([
            html.Label("Select Counterparty"),
            dcc.Dropdown(
                id="counterparty-dropdown",
                options=[{"label": c, "value": c} for c in df_counterparty["Counterparty"].unique()],
                placeholder="Select Counterparty"
            ),
            html.Label("Select Product"),
            dcc.Dropdown(
                id="product-dropdown",
                options=[{"label": p, "value": p} for p in df_counterparty["Product"].unique()],
                placeholder="Select Product"
            ),
            html.Label("Select Debit/Credit"),
            dcc.Dropdown(
                id="debit-credit-dropdown",
                options=[{"label": "Debit", "value": "Debit"}, {"label": "Credit", "value": "Credit"}],
                placeholder="Select Debit/Credit"
            ),
            html.Label("Enter Amount"),
            dbc.Input(id="amount-input", type="number", placeholder="Enter Amount"),
            html.Br(),
            dbc.Button("Apply Transaction", id="apply-btn", color="primary", className="mt-2"),
            dbc.Button("Reset", id="reset-btn", color="secondary", className="mt-2 ms-2"),
            dbc.Button("Export Simulation", id="export-btn", color="success", className="mt-2 ms-2")
        ], width=4),
        dbc.Col([
            dash_table.DataTable(id="counterparty-table", data=df_counterparty.to_dict("records"), page_size=6),
            html.Br(),
            dash_table.DataTable(id="lcr-kpi-table", data=df_lcr.to_dict("records"), page_size=6)
        ], width=8)
    ]),

    # Gauge Chart and Simulation Table
    html.Br(),
    dcc.Graph(id="lcr-gauge-chart", figure=create_gauge(df_lcr.iloc[-1]['Value'])),
    html.Br(),
    dash_table.DataTable(id="simulation-table", data=df_simulations.to_dict("records"), page_size=6)
])

@app.callback(
    [Output("simulation-table", "data"),
     Output("lcr-gauge-chart", "figure"),
     Output("lcr-kpi-table", "data")],
    Input("apply-btn", "n_clicks"),
    [State("counterparty-dropdown", "value"),
     State("product-dropdown", "value"),
     State("debit-credit-dropdown", "value"),
     State("amount-input", "value")],
    prevent_initial_call=True
)
def apply_transaction(n_clicks, counterparty, product, debit_credit, amount):
    """Applies transaction and updates LCR"""
    if counterparty and product and debit_credit and amount:
        # Determine LCR impact based on product and transaction type
        impact_category = "HQLA" if product in ["Bonds", "Central Bank Reserves"] else "Inflows" if debit_credit == "Debit" else "Outflows"
        
        # Calculate new LCR
        current_lcr = df_lcr.iloc[-1]['Value']
        new_lcr = current_lcr - amount if debit_credit == "Debit" else current_lcr + amount
        
        # Append new transaction to simulation table
        new_entry = {
            "Counterparty": counterparty,
            "Product": product,
            "Amount": amount,
            "Debit/Credit": debit_credit,
            "New LCR %": new_lcr,
            "Affected Category": impact_category
        }
        global df_simulations
        df_simulations = pd.concat([df_simulations, pd.DataFrame([new_entry])], ignore_index=True)

        # Update LCR table
        updated_lcr_data = df_lcr.copy()
        updated_lcr_data.iloc[-1, 1] = new_lcr

        return df_simulations.to_dict("records"), create_gauge(new_lcr), updated_lcr_data.to_dict("records")
    return dash.no_update

@app.callback(
    [Output("counterparty-table", "data"),
     Output("lcr-kpi-table", "data"),
     Output("simulation-table", "data"),
     Output("lcr-gauge-chart", "figure")],
    Input("reset-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_data(n_clicks):
    """Resets the data to original state"""
    global df_simulations
    df_simulations = pd.DataFrame(columns=["Counterparty", "Product", "Amount", "Debit/Credit", "New LCR %", "Affected Category"])
    return (df_counterparty.to_dict("records"), 
            df_lcr.to_dict("records"), 
            df_simulations.to_dict("records"), 
            create_gauge(df_lcr.iloc[-1]['Value']))

if __name__ == '__main__':
    webbrowser.open_new("http://localhost:8050")
    app.run_server(debug=True, use_reloader=False, host="0.0.0.0", port=8050)


# In[ ]:




