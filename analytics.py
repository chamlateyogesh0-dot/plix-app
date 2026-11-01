class SmartAnalytics:

    @staticmethod
    def calculate_profit_margin(buy_price: float, sell_target_price: float) -> dict:
        """Reseller / Seller Profit Margin Calculation"""
        if buy_price <= 0:
            return {"profit_amount": 0.0, "profit_percentage": 0.0}
        
        profit_amount = sell_target_price - buy_price
        profit_percentage = (profit_amount / buy_price) * 100
        
        return {
            "buy_price": buy_price,
            "sell_target_price": sell_target_price,
            "profit_amount": round(profit_amount, 2),
            "profit_percentage": round(profit_percentage, 2)
        }

    @staticmethod
    def get_smart_buy_indicator(current_price: float, price_history: list) -> str:
        """
        Smart Buy Indicator Badge Logic:
        🟢 Great Deal (Lowest price in last history)
        🟡 Average Price (Standard price)
        🔴 Bad Time to Buy / Price Hike
        """
        if not price_history:
            return "Average Price"
        
        min_price = min(price_history)
        max_price = max(price_history)
        
        if current_price <= min_price:
            return "Great Deal"
        elif current_price >= max_price:
            return "Bad Time to Buy"
        else:
            return "Average Price"