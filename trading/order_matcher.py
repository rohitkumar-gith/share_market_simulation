"""
Order Matcher - Matches Buy/Sell orders and executes trades
"""
from database.db_manager import db
from models.transaction import Transaction
from models.company import Company
from models.user import User
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderMatcher:
    """Matches pending buy and sell orders"""
    
    def match_all_orders(self):
        """Run matching algorithm for all companies"""
        companies = Company.get_all()
        total_matches = 0
        
        for company in companies:
            try:
                matches = self.match_orders_for_company(company.company_id)
                total_matches += matches
            except Exception as e:
                logger.error(f"Error matching orders for {company.company_name}: {e}")
                
        return {'total_matches': total_matches, 'timestamp': datetime.now()}

    def match_orders_for_company(self, company_id):
        """Match orders for a specific company"""
        # Get pending buy orders (Highest Price First, then Oldest)
        buy_orders = db.execute_query("""
            SELECT * FROM share_orders 
            WHERE company_id = ? AND order_type = 'buy' AND status = 'pending'
            ORDER BY price_per_share DESC, created_at ASC
        """, (company_id,))
        
        # Get pending sell orders (Lowest Price First, then Oldest)
        sell_orders = db.execute_query("""
            SELECT * FROM share_orders 
            WHERE company_id = ? AND order_type = 'sell' AND status = 'pending'
            ORDER BY price_per_share ASC, created_at ASC
        """, (company_id,))
        
        if not buy_orders or not sell_orders:
            return 0
            
        matches = 0
        buy_orders = [dict(row) for row in buy_orders]
        sell_orders = [dict(row) for row in sell_orders]
        
        buy_idx = 0
        sell_idx = 0
        
        while buy_idx < len(buy_orders) and sell_idx < len(sell_orders):
            buy = buy_orders[buy_idx]
            sell = sell_orders[sell_idx]
            
            # Check if price matches (Buy Price >= Sell Price)
            if buy['price_per_share'] >= sell['price_per_share']:
                # MATCH FOUND!
                trade_qty = min(buy['quantity'], sell['quantity'])
                trade_price = sell['price_per_share']  # Buyer pays seller's asking price
                
                # Execute Trade
                self._execute_trade(buy, sell, trade_qty, trade_price)
                
                # Update local quantities
                buy['quantity'] -= trade_qty
                sell['quantity'] -= trade_qty
                matches += 1
                
                # Move to next order if fully filled
                if buy['quantity'] == 0:
                    buy_idx += 1
                if sell['quantity'] == 0:
                    sell_idx += 1
            else:
                break
                
        return matches

    def _execute_trade(self, buy_order, sell_order, quantity, price):
        """Execute the matched trade"""
        buyer_id = buy_order['user_id']
        seller_id = sell_order['user_id']
        company_id = buy_order['company_id']
        total_amount = quantity * price
        
        try:
            # 1. Update/Close Buy Order
            if buy_order['quantity'] == quantity:
                db.execute_update("UPDATE share_orders SET status = 'completed', completed_at = ? WHERE order_id = ?",
                                (datetime.now(), buy_order['order_id']))
                
                # Refund difference
                locked_amount = buy_order['price_per_share'] * quantity
                refund = locked_amount - total_amount
                if refund > 0:
                    User.get_by_id(buyer_id).add_funds(refund, "Refund on trade price difference")
            else:
                db.execute_update("UPDATE share_orders SET quantity = quantity - ? WHERE order_id = ?",
                                (quantity, buy_order['order_id']))
            
            # 2. Update/Close Sell Order
            if sell_order['quantity'] == quantity:
                db.execute_update("UPDATE share_orders SET status = 'completed', completed_at = ? WHERE order_id = ?",
                                (datetime.now(), sell_order['order_id']))
            else:
                db.execute_update("UPDATE share_orders SET quantity = quantity - ? WHERE order_id = ?",
                                (quantity, sell_order['order_id']))

            # 3. Transfer Shares (Add to Buyer)
            db.add_or_update_holding(buyer_id, company_id, quantity, price)
            
            # 4. Transfer Money (Add to Seller)
            User.get_by_id(seller_id).add_funds(total_amount, f"Sold {quantity} shares via order match")
            
            # 5. Record Transaction
            db.add_transaction(buyer_id, company_id, quantity, price, 'trade', seller_id)
            
            # 6. UPDATE COMPANY PRICE (CRITICAL IMPROVEMENT)
            # This makes the market react immediately to the trade
            db.execute_update("UPDATE companies SET share_price = ? WHERE company_id = ?", (price, company_id))
            db.execute_insert("INSERT INTO price_history (company_id, price) VALUES (?, ?)", (company_id, price))
            
            print(f"Trade Executed: {quantity} shares of Co:{company_id} @ {price}")
            
        except Exception as e:
            print(f"Trade Execution Failed: {e}")

order_matcher = OrderMatcher()