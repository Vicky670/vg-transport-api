from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="V.G Transport Booking API with Database")
from fastapi.middleware.cors import CORSMiddleware

# ... (Unga pazhaiya code mela irukkum) ...
app = FastAPI(title="V.G Transport Booking API with Database")

# Itha pudhusa add pannunga
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Yellam websites-um intha API kooda pesa allow pandrom
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ... (Keela unga database matrum matha code apdiye irukkatum) ...

# --- Database Setup (Server start aagum pothu Table create aagum) ---
def init_db():
    conn = sqlite3.connect("vg_transport.db")
    cursor = conn.cursor()
    
    # Truck details save panna oru Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trucks (
            truck_id TEXT PRIMARY KEY,
            model TEXT,
            capacity_tons REAL,
            price_per_km REAL,
            is_available BOOLEAN
        )
    ''')
    
    # Booking details save panna inoru Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            truck_id TEXT,
            distance_km REAL,
            total_price REAL
        )
    ''')
    conn.commit()
    conn.close()

# Intha function-a call pandrom
init_db()

# --- Data Models ---
class Truck(BaseModel):
    truck_id: str
    model: str
    capacity_tons: float
    price_per_km: float
    is_available: bool = True

class BookingRequest(BaseModel):
    customer_name: str
    truck_id: str
    distance_km: float

# --- API Endpoints ---

@app.get("/")
def home():
    return {"message": "V.G Transport Database API is running!"}

@app.post("/add_truck")
def add_truck(truck: Truck):
    conn = sqlite3.connect("vg_transport.db")
    cursor = conn.cursor()
    try:
        # Puthu vandiya Database-la insert pandrom
        cursor.execute("INSERT INTO trucks VALUES (?, ?, ?, ?, ?)", 
                       (truck.truck_id, truck.model, truck.capacity_tons, truck.price_per_km, truck.is_available))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Truck ID already exists in Database")
    
    conn.close()
    return {"message": f"{truck.model} added successfully to the Database!"}

@app.get("/available_trucks")
def get_available_trucks():
    conn = sqlite3.connect("vg_transport.db")
    cursor = conn.cursor()
    # Free-ya irukka vandiya mattum database-la irunthu thedurom (1 = True)
    cursor.execute("SELECT truck_id, model, capacity_tons, price_per_km FROM trucks WHERE is_available = 1")
    trucks = cursor.fetchall()
    conn.close()
    
    available = [{"truck_id": t[0], "model": t[1], "capacity_tons": t[2], "price_per_km": t[3]} for t in trucks]
    return {"available_trucks": available}

@app.post("/book_truck")
def book_truck(request: BookingRequest):
    conn = sqlite3.connect("vg_transport.db")
    cursor = conn.cursor()
    
    # Vandi irukka, free-ya irukka nu check pandrom
    cursor.execute("SELECT price_per_km FROM trucks WHERE truck_id = ? AND is_available = 1", (request.truck_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=400, detail="Truck not available or not found")
        
    price_per_km = result[0]
    total_price = price_per_km * request.distance_km
    
    # Vandiya "Booked" (0 = False) nu mathurom
    cursor.execute("UPDATE trucks SET is_available = 0 WHERE truck_id = ?", (request.truck_id,))
    
    # Booking history-a save pandrom
    cursor.execute("INSERT INTO bookings (customer_name, truck_id, distance_km, total_price) VALUES (?, ?, ?, ?)",
                   (request.customer_name, request.truck_id, request.distance_km, total_price))
    
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "message": "Booking Saved in Database!", 
        "booking_id": f"BKG{booking_id}", 
        "total_price": total_price
    }
   
@app.post("/complete_ride/{truck_id}")
def complete_ride(truck_id: str):
    conn = sqlite3.connect("vg_transport.db")
    cursor = conn.cursor()
    
    # Vandi database-la irukka nu check pandrom
    cursor.execute("SELECT is_available FROM trucks WHERE truck_id = ?", (truck_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Truck not found in Database")
        
    # Vandiya marubadiyum "Available" (1 = True) nu maathurom
    cursor.execute("UPDATE trucks SET is_available = 1 WHERE truck_id = ?", (truck_id,))
    conn.commit()
    conn.close()
    
    return {"message": f"✅ Ride completed! Truck {truck_id} is now available for next booking."}
    # --- TRIP MUDINJA PIRAGU VANDIYA FREE AAKKUM FUNCTION ---
@app.post("/end_trip/{truck_id}")
def end_trip(truck_id: str):
    conn = sqlite3.connect("vg_transport.db")
    cursor = conn.cursor()
    
    # Vandi database-la irukka nu check pandrom
    cursor.execute("SELECT * FROM trucks WHERE truck_id=?", (truck_id,))
    truck = cursor.fetchone()
    
    if not truck:
        conn.close()
        raise HTTPException(status_code=404, detail="Intha vandi database-la illai!")
        
    # Vandiyoda status-a thirumba "Free" (is_available = 1) nu maathurom
    cursor.execute("UPDATE trucks SET is_available = 1 WHERE truck_id=?", (truck_id,))
    conn.commit()
    conn.close()
    
    return {"message": f"Trip Mudinjiduchu! {truck_id} vandi ippo adutha booking-kku ready aagiduchu."}