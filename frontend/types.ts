export interface RawData {
  census: { median_income: number; resident_base: number; bachelors_rate: number };
  housing: { median_rent: number; rent_to_income: number };
  broadband: { broadband_pct: number; fiber_pct: number; cable_pct: number };
  health: { hospitals: number; primary_care_centers: number; is_hpsa: boolean };
  crime: { crime_per_1k: number };
  osm: { parks: number; transit_stops: number; grocery_stores: number; clinics: number };
  air_quality: { aqi: number; category: string; pollutant: string };
}

export interface CivicScores {
  Safety: number;
  Health: number;
  Education: number;
  EconomicOpportunity: number;
  HousingAffordability: number;
  DigitalAccess: number;
  Environment: number;
  Accessibility: number;
  OverallCivicScore: number;
}

export interface ZipAnalysis {
  zip_code: string;
  raw_data: RawData;
  scores: CivicScores;
  location?: { lat: number; lon: number };
}

export interface ChatResponse {
  reply: string;
}
