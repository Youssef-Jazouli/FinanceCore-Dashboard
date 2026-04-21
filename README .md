# FinanceCore Dashboard

A Streamlit-based business intelligence dashboard for banking analytics, providing executive-level performance views and risk scoring analysis powered by a PostgreSQL database.

---

## Features

- **Vue Executive** — High-level KPIs, monthly revenue trends, agency/product breakdown, and client segment distribution
- **Analyse des Risques** — Credit score correlation matrix, risk scatter plots, and a ranked top-10 at-risk client table with CSV export
- **Global Filters** — Filter all views by agency, client segment, banking product, and year range via an interactive sidebar

---

## Prerequisites

- Python 3.8+
- A running PostgreSQL instance with the `financecore_db` database

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/financecore-dashboard.git
cd financecore-dashboard

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Required packages

```
streamlit
pandas
sqlalchemy
psycopg2-binary
plotly
python-dotenv
```

---

## Configuration

Create a `.env` file in the project root with your database credentials:

```env
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=financecore_db
```

---

## Database Schema

The dashboard expects the following tables in PostgreSQL:

| Table | Key Columns |
|-------|-------------|
| `transaction` | `transaction_id`, `montant`, `type_operation`, `date_transaction`, `statut`, `compte_id` |
| `compte` | `compte_id`, `client_id`, `produit_id`, `agence_id` |
| `client` | `client_id`, `nom_segment`, `score_credit_client` |
| `produit` | `produit_id`, `nom_produit` |
| `agence` | `agence_id`, `nom_agence` |

---

## Usage

```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`.

---

## Pages

### Vue Executive
Displays four KPI cards at the top:
- **Volume Transactions** — Total number of transactions
- **Chiffre d'Affaires** — Sum of all credit operations
- **Clients Actifs** — Count of unique active clients
- **Marge Moyenne (15%)** — Estimated margin at 15% of revenue

Charts include monthly evolution by transaction type, revenue by agency and product, and client distribution by segment.

### Analyse des Risques
- **Correlation Matrix** — Heatmap of `score_credit`, `montant_total`, and `taux_rejet`
- **Scatter Plot** — Credit score vs. total transaction amount, colored by risk category (Risqué / Standard / Premium)
- **Top 10 Clients à Risque** — Sorted by lowest credit score and highest rejection rate, with color-coded risk levels and a CSV export button

#### Risk categorization logic

| Credit Score | Category |
|---|---|
| < 400 | Risqué |
| 400 – 699 | Standard |
| ≥ 700 | Premium |

---

## Project Structure

```
financecore-dashboard/
├── app.py           # Main application file
├── .env             # Environment variables (not committed)
├── .env.example     # Example environment file
├── requirements.txt # Python dependencies
└── README.md
```

---

## License

This project is proprietary to FinanceCore SA. All rights reserved.
