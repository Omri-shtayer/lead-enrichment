# SimilarWeb Lead Enrichment Sample Generator

A Streamlit application that generates sample lead enrichment data using the SimilarWeb API. This tool allows users to fetch metadata and time series data for multiple domains.

## 🌐 Live App

Access the live app here: [SimilarWeb Lead Enrichment Generator](https://similarweb-lead-enrichment.streamlit.app)

## ✨ Features

- Fetch lead enrichment data for multiple domains (up to 100)
- Generate both metadata and time series CSV files
- Support for date range selection
- Country-specific data filtering
- Mobile/Desktop share metrics
- Traffic source analysis
- Geographic distribution data
- Easy-to-use interface with example domains

## 💻 Usage

1. Enter your SimilarWeb API key
2. Select date range (YYYY-MM format)
3. Choose target country
4. Enter domains (one per line)
5. Click "Generate CSV" to process
6. Download individual or combined CSV files

## 💳 Data Credits

Each domain processed will cost 25 data credits from your SimilarWeb API quota.

## 🛠️ Local Development

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/similarweb-lead-enrichment.git
cd similarweb-lead-enrichment
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run app.py
```

## 🚀 Deployment

This app is deployed using [Streamlit Cloud](https://streamlit.io/cloud). To deploy your own version:

1. Fork this repository
2. Sign up for [Streamlit Cloud](https://share.streamlit.io)
3. Create a new app and select your forked repository
4. Deploy!

## 📝 License

This project is licensed under the MIT License. 