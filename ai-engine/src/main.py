CLI entry point for running forecasts and analysis.
"""
import argparse
from src.forecast import train_and_forecast
from src.seasonal import analyze_seasonal_effects


def main():
    parser = argparse.ArgumentParser(description="Poultry Market AI Engine")
    parser.add_argument("action", choices=["forecast", "seasonal"])
    parser.add_argument("--product", default="fertilized_eggs")
    parser.add_argument("--periods", type=int, default=90)
    parser.add_argument("--years", type=int, default=3)
    args = parser.parse_args()

    if args.action == "forecast":
        result = train_and_forecast(args.product, periods=args.periods, years=args.years)
        if result is not None:
            print(result.tail(10))
        else:
            print("No data available for forecasting.")

    elif args.action == "seasonal":
        result = analyze_seasonal_effects(args.product, years=args.years)
        print(result)


if __name__ == "__main__":
    main()
