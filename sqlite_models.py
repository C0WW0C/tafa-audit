# ============================================================
# TAFA V7 PRO
# SQLITE MODELS FINAL
# ============================================================


from dataclasses import dataclass



@dataclass
class TradeModel:


    symbol:str

    side:str

    price:float

    qty:float

    pnl:float=0



@dataclass
class SignalModel:


    symbol:str

    signal:str

    confidence:float



@dataclass
class PositionModel:


    symbol:str

    qty:float

    entry:float