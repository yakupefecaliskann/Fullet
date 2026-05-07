const Map<String, Map<String, Map<String, dynamic>>> carDatabase = {
  "Fiat": {
    "Egea 1.3 Multijet": {"fuel": "Motorin", "tank": 50.0, "cons": 4.1},
    "Egea 1.4 Fire": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 6.4},
    "Egea 1.6 Multijet": {"fuel": "Motorin", "tank": 50.0, "cons": 4.5},
    "Fiorino 1.3 Multijet": {"fuel": "Motorin", "tank": 45.0, "cons": 4.5},
    "Fiorino 1.4 Eco": {"fuel": "LPG", "tank": 45.0, "cons": 7.2},
    "Linea 1.3 Multijet": {"fuel": "Motorin", "tank": 45.0, "cons": 4.9},
    "Doblo 1.6 Multijet": {"fuel": "Motorin", "tank": 60.0, "cons": 5.5}
  },
  "Renault": {
    "Clio 1.5 dCi": {"fuel": "Motorin", "tank": 42.0, "cons": 3.6},
    "Clio 1.0 TCe": {"fuel": "Kursunsuz 95", "tank": 42.0, "cons": 5.0},
    "Clio 1.2 Joy": {"fuel": "Kursunsuz 95", "tank": 45.0, "cons": 5.5},
    "Symbol 1.5 dCi": {"fuel": "Motorin", "tank": 50.0, "cons": 4.2},
    "Symbol 1.2 16V": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 5.9},
    "Megane 1.3 TCe": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 5.4},
    "Megane 1.5 dCi": {"fuel": "Motorin", "tank": 50.0, "cons": 4.0},
    "Fluence 1.5 dCi": {"fuel": "Motorin", "tank": 60.0, "cons": 4.5},
    "Captur 1.3 TCe": {"fuel": "Kursunsuz 95", "tank": 48.0, "cons": 5.5}
  },
  "Volkswagen": {
    "Polo 1.0 TSI": {"fuel": "Kursunsuz 95", "tank": 40.0, "cons": 5.5},
    "Polo 1.4 TDI": {"fuel": "Motorin", "tank": 45.0, "cons": 3.8},
    "Golf 1.5 eTSI": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 5.8},
    "Golf 1.6 TDI": {"fuel": "Motorin", "tank": 50.0, "cons": 4.1},
    "Passat 2.0 TDI": {"fuel": "Motorin", "tank": 66.0, "cons": 4.6},
    "Passat 1.5 TSI": {"fuel": "Kursunsuz 95", "tank": 66.0, "cons": 5.3},
    "Jetta 1.6 TDI": {"fuel": "Motorin", "tank": 55.0, "cons": 4.5},
    "T-Roc 1.5 TSI": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 6.1}
  },
  "Toyota": {
    "Corolla 1.5 Vision": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 5.8},
    "Corolla 1.6 Valvematic": {
      "fuel": "Kursunsuz 95",
      "tank": 55.0,
      "cons": 6.0
    },
    "Corolla 1.8 Hybrid": {"fuel": "Kursunsuz 95", "tank": 43.0, "cons": 3.8},
    "Corolla 1.4 D-4D": {"fuel": "Motorin", "tank": 55.0, "cons": 4.3},
    "Yaris 1.5 Hybrid": {"fuel": "Kursunsuz 95", "tank": 36.0, "cons": 3.2},
    "Hilux 2.4 D-4D": {"fuel": "Motorin", "tank": 80.0, "cons": 7.5}
  },
  "Honda": {
    "Civic 1.5 VTEC": {"fuel": "Kursunsuz 95", "tank": 47.0, "cons": 6.5},
    "Civic 1.6 i-DTEC": {"fuel": "Motorin", "tank": 46.0, "cons": 4.1},
    "Civic 1.6 Eco": {"fuel": "LPG", "tank": 46.0, "cons": 7.0},
    "City 1.5 i-VTEC": {"fuel": "Kursunsuz 95", "tank": 40.0, "cons": 6.2},
    "CR-V 1.5 VTEC": {"fuel": "Kursunsuz 95", "tank": 57.0, "cons": 7.2}
  },
  "Dacia": {
    "Duster 1.5 dCi": {"fuel": "Motorin", "tank": 50.0, "cons": 4.8},
    "Duster 1.0 TCe ECO-G": {"fuel": "LPG", "tank": 50.0, "cons": 6.8},
    "Sandero 1.0 TCe": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 5.3},
    "Sandero Stepway 1.5 dCi": {"fuel": "Motorin", "tank": 50.0, "cons": 4.2},
    "Logan 1.5 dCi": {"fuel": "Motorin", "tank": 50.0, "cons": 4.5}
  },
  "Peugeot": {
    "208 1.2 PureTech": {"fuel": "Kursunsuz 95", "tank": 44.0, "cons": 5.2},
    "208 1.5 BlueHDi": {"fuel": "Motorin", "tank": 41.0, "cons": 3.5},
    "308 1.2 PureTech": {"fuel": "Kursunsuz 95", "tank": 52.0, "cons": 5.5},
    "2008 1.5 BlueHDi": {"fuel": "Motorin", "tank": 44.0, "cons": 3.8},
    "3008 1.5 BlueHDi": {"fuel": "Motorin", "tank": 53.0, "cons": 4.1}
  },
  "Hyundai": {
    "i20 1.4 MPI": {"fuel": "Kursunsuz 95", "tank": 40.0, "cons": 6.3},
    "i20 1.2 D-CVVT": {"fuel": "Kursunsuz 95", "tank": 50.0, "cons": 5.5},
    "i10 1.0 MPI": {"fuel": "Kursunsuz 95", "tank": 36.0, "cons": 4.9},
    "Tucson 1.6 CRDi": {"fuel": "Motorin", "tank": 54.0, "cons": 5.7},
    "Tucson 1.6 T-GDI": {"fuel": "Kursunsuz 95", "tank": 54.0, "cons": 7.2}
  },
  "Ford": {
    "Focus 1.5 TDCi": {"fuel": "Motorin", "tank": 47.0, "cons": 4.2},
    "Focus 1.0 EcoBoost": {"fuel": "Kursunsuz 95", "tank": 52.0, "cons": 5.5},
    "Fiesta 1.4 TDCi": {"fuel": "Motorin", "tank": 43.0, "cons": 4.1},
    "Fiesta 1.0 EcoBoost": {"fuel": "Kursunsuz 95", "tank": 42.0, "cons": 4.8},
    "Courier 1.5 TDCi": {"fuel": "Motorin", "tank": 47.0, "cons": 4.5},
    "Puma 1.0 EcoBoost": {"fuel": "Kursunsuz 95", "tank": 42.0, "cons": 5.8}
  },
  "Opel": {
    "Astra 1.6 CDTI": {"fuel": "Motorin", "tank": 48.0, "cons": 4.0},
    "Astra 1.4 Turbo": {"fuel": "Kursunsuz 95", "tank": 48.0, "cons": 5.5},
    "Corsa 1.2 Turbo": {"fuel": "Kursunsuz 95", "tank": 44.0, "cons": 5.3},
    "Corsa 1.5 Diesel": {"fuel": "Motorin", "tank": 41.0, "cons": 3.6},
    "Mokka 1.2 Turbo": {"fuel": "Kursunsuz 95", "tank": 44.0, "cons": 5.9}
  }
};
