def calculate_sl_tp(entry_price, direction, atr, rr_ratio):
    sl_multiplier = 1.5 * atr
    if direction.upper() == 'LONG':
        stop_loss = entry_price - sl_multiplier
        take_profit = entry_price + (sl_multiplier * rr_ratio)
    elif direction.upper() == 'SHORT':
        stop_loss = entry_price + sl_multiplier
        take_profit = entry_price - (sl_multiplier * rr_ratio)
    else:
        return None, None
    return round(stop_loss, 2), round(take_profit, 2)

def calculate_position_size(balance, risk_percent, entry_price, stop_loss_price):
    capital_at_risk = balance * (risk_percent / 100)
    risk_per_unit = abs(entry_price - stop_loss_price)
    if risk_per_unit == 0: return 0
    return round(capital_at_risk / risk_per_unit, 4)