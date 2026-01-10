from app.jobs.bulk_population import populate_all_stocks

if __name__ == "__main__":
    # This will skip the first 7 batches and finish the rest
    populate_all_stocks(resume=True)
    