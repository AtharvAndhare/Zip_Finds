import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import {
  ChevronLeft, AlertCircle, Loader2, Send,
  DollarSign, Home as HomeIcon, Wifi, Heart, Bot,
  Wind, Shield, GraduationCap, Car, Leaf, MapPin
} from 'lucide-react';
import { analyzeZip, chatWithZip, fetchNarrative } from '../services/api';
import { ZipAnalysis } from '../types';

/** Forces Leaflet to recalculate tile grid after mount / resize */
const InvalidateSize: React.FC = () => {
  const map = useMap();
  useEffect(() => {
    // Small delay to ensure the container is fully rendered
    const timer = setTimeout(() => map.invalidateSize(), 300);
    return () => clearTimeout(timer);
  }, [map]);
  return null;
};

/** Re-centers map when coordinates change */
const RecenterMap: React.FC<{ lat: number; lon: number }> = ({ lat, lon }) => {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], 12);
    setTimeout(() => map.invalidateSize(), 300);
  }, [lat, lon, map]);
  return null;
};

const Analysis: React.FC = () => {
  const { zip } = useParams<{ zip: string }>();
  const [data, setData] = useState<ZipAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'ai'; text: string }[]>([]);
  const [isChatting, setIsChatting] = useState(false);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!zip) return;
      setLoading(true);
      setError(null);
      setNarrative(null);
      setChatHistory([]);
      try {
        const result = await analyzeZip(zip);
        setData(result);
        // Fetch narrative in background after data loads
        setNarrativeLoading(true);
        fetchNarrative(zip, result.scores, 'General')
          .then((res) => setNarrative(res.narrative))
          .catch(() => setNarrative('Unable to generate narrative at this time.'))
          .finally(() => setNarrativeLoading(false));
      } catch (err: any) {
        console.error('API Error:', err);
        setError(
          err.response?.data?.error ||
          'Failed to connect to the Zip Finds API. Please ensure the Python backend is running at ' +
          ((import.meta as any).env?.VITE_API_URL || 'http://localhost:5000')
        );
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [zip]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim() || !data || isChatting) return;

    const userQuery = chatMessage;
    setChatHistory((prev) => [...prev, { role: 'user', text: userQuery }]);
    setChatMessage('');
    setIsChatting(true);

    try {
      const response = await chatWithZip(data.zip_code, userQuery, data.scores);
      setChatHistory((prev) => [...prev, { role: 'ai', text: response.reply }]);
    } catch (err: any) {
      console.error('Chat Error:', err);
      setChatHistory((prev) => [
        ...prev,
        { role: 'ai', text: 'Error: ' + (err.response?.data?.reply || 'Network issue with AI processor.') },
      ]);
    } finally {
      setIsChatting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-16 w-16 text-brand animate-spin mb-6" />
        <p className="text-black font-black uppercase tracking-widest text-xs">
          Decoding Local Infrastructure for {zip}...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto mt-20 p-12 bg-white rounded-[3rem] border border-black/10 shadow-2xl">
        <div className="flex items-center space-x-4 text-black mb-8">
          <AlertCircle className="h-10 w-10 text-brand" />
          <h2 className="text-3xl font-black uppercase tracking-tighter">API Disconnect</h2>
        </div>
        <p className="text-black/60 mb-10 font-medium leading-relaxed">{error || 'Data retrieval failed.'}</p>
        <Link
          to="/"
          className="px-8 py-4 bg-black text-white font-black uppercase tracking-widest rounded-2xl hover:bg-brand transition-colors inline-flex items-center"
        >
          <ChevronLeft className="h-4 w-4 mr-2" /> Return to Dashboard
        </Link>
      </div>
    );
  }

  const scoreLabels = [
    'Safety', 'Health', 'Education', 'Opportunity',
    'Housing', 'Digital', 'Environment', 'Accessibility',
  ];

  const scoreValues = [
    data.scores.Safety, data.scores.Health, data.scores.Education,
    data.scores.EconomicOpportunity, data.scores.HousingAffordability,
    data.scores.DigitalAccess, data.scores.Environment, data.scores.Accessibility,
  ];

  // Map coordinates — use backend-provided location, fallback to NYC
  const lat = data.location?.lat ?? 40.7128;
  const lon = data.location?.lon ?? -74.006;

  // Format helpers
  const fmtDollar = (v: number) => `$${v.toLocaleString()}`;
  const fmtPct = (v: number) => (v > 1 ? `${v.toFixed(1)}%` : `${(v * 100).toFixed(1)}%`);

  return (
    <div className="max-w-7xl mx-auto px-4 py-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8 pb-8 border-b border-black/5">
        <div>
          <Link
            to="/"
            className="inline-flex items-center text-black/40 mb-4 hover:text-brand text-xs font-black uppercase tracking-widest"
          >
            <ChevronLeft className="h-3 w-3 mr-1" /> Back
          </Link>
          <h1 className="text-6xl font-black text-black uppercase tracking-tighter">
            REGION <span className="text-brand">{data.zip_code}</span>
          </h1>
        </div>
        <div className="flex items-center space-x-10">
          <div className="text-right">
            <span className="text-[10px] text-black/40 uppercase tracking-[0.3em] font-black">Composite Score</span>
            <div className="text-6xl font-black text-black leading-none">
              {data.scores.OverallCivicScore}
              <span className="text-lg text-black/20">/100</span>
            </div>
          </div>
          <div className="h-20 w-20 bg-black rounded-3xl flex items-center justify-center text-white text-4xl font-black">
            {data.scores.OverallCivicScore >= 80 ? 'A' : data.scores.OverallCivicScore >= 60 ? 'B' : data.scores.OverallCivicScore >= 40 ? 'C' : 'D'}
          </div>
        </div>
      </div>

      {/* Radar Chart + Chat + Map */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* Radar Chart */}
        <div className="lg:col-span-2 bg-white p-8 md:p-12 rounded-[3rem] border border-black/5 shadow-sm overflow-hidden h-fit">
          <h3 className="text-xs font-black text-black/30 uppercase tracking-[0.3em] mb-10">Performance Vector</h3>
          <div className="w-full flex justify-center">
            <Plot
              data={[
                {
                  type: 'scatterpolar',
                  r: [...scoreValues, scoreValues[0]],
                  theta: [...scoreLabels, scoreLabels[0]],
                  fill: 'toself',
                  fillcolor: 'rgba(85, 107, 47, 0.1)',
                  line: { color: '#556b2f', width: 3 },
                  marker: { size: 8, color: '#000' },
                },
              ]}
              layout={{
                polar: {
                  radialaxis: { visible: true, range: [0, 100], gridcolor: '#f0f0f0' },
                  angularaxis: { gridcolor: '#f0f0f0', font: { size: 10 } },
                },
                showlegend: false,
                margin: { l: 40, r: 40, t: 20, b: 20 },
                height: 450,
                width: 550,
                autosize: true,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
              }}
              config={{ responsive: true, displayModeBar: false }}
            />
          </div>
        </div>

        {/* Right Column: Chat + Map */}
        <div className="space-y-8">
          {/* AI Chat */}
          <div className="bg-black p-8 rounded-[3rem] shadow-xl text-white">
            <h3 className="text-xs font-black text-white/40 uppercase tracking-[0.3em] mb-6 flex items-center">
              <Bot className="h-4 w-4 mr-2 text-brand" />
              Intelligence Lead
            </h3>
            <div className="h-64 overflow-y-auto mb-6 space-y-4 pr-2 text-sm">
              {chatHistory.length === 0 && (
                <p className="text-white/20 italic text-center mt-12">
                  System ready. Ask about local metrics...
                </p>
              )}
              {chatHistory.map((chat, i) => (
                <div key={i} className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`px-4 py-2 rounded-2xl max-w-[85%] ${
                      chat.role === 'user'
                        ? 'bg-brand text-white'
                        : 'bg-white/10 text-white border border-white/5'
                    }`}
                  >
                    {chat.text}
                  </div>
                </div>
              ))}
              {isChatting && <div className="animate-pulse text-brand font-bold">Analyst is typing...</div>}
              <div ref={chatEndRef} />
            </div>
            <form onSubmit={handleChat} className="relative">
              <input
                type="text"
                placeholder="Ask the AI Analyst..."
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm outline-none focus:ring-1 focus:ring-brand"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
              />
              <button type="submit" className="absolute right-2 top-2 p-1.5 text-brand">
                <Send size={18} />
              </button>
            </form>
          </div>

          {/* Map */}
          <div className="bg-white rounded-[3rem] border border-black/5 shadow-sm h-64 overflow-hidden relative">
            <MapContainer center={[lat, lon]} zoom={12} scrollWheelZoom={false}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Marker position={[lat, lon]}>
                <Popup>ZIP {data.zip_code}</Popup>
              </Marker>
              <InvalidateSize />
              <RecenterMap lat={lat} lon={lon} />
            </MapContainer>
          </div>
        </div>
      </div>

      {/* Data Cards Grid */}
      <h2 className="text-2xl font-black text-black mt-20 mb-8 uppercase tracking-tighter">Attribute Explorer</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard icon={<DollarSign />} title="Finance" items={[
          { label: 'Median Income', value: fmtDollar(data.raw_data.census.median_income) },
          { label: 'Population', value: data.raw_data.census.resident_base.toLocaleString() },
        ]} />
        <MetricCard icon={<GraduationCap />} title="Education" items={[
          { label: "Bachelor's+", value: fmtPct(data.raw_data.census.bachelors_rate) },
        ]} />
        <MetricCard icon={<HomeIcon />} title="Housing" items={[
          { label: 'Median Rent', value: fmtDollar(data.raw_data.housing.median_rent) },
          { label: 'Rent / Income', value: fmtPct(data.raw_data.housing.rent_to_income) },
        ]} />
        <MetricCard icon={<Heart />} title="Wellness" items={[
          { label: 'Hospitals', value: String(data.raw_data.health.hospitals) },
          { label: 'Designation', value: data.raw_data.health.is_hpsa ? 'HPSA' : 'Standard' },
        ]} />
        <MetricCard icon={<Wifi />} title="Digital Access" items={[
          { label: 'Broadband', value: fmtPct(data.raw_data.broadband.broadband_pct) },
          { label: 'Fiber', value: fmtPct(data.raw_data.broadband.fiber_pct) },
          { label: 'Cable', value: fmtPct(data.raw_data.broadband.cable_pct) },
        ]} />
        <MetricCard icon={<Shield />} title="Safety" items={[
          { label: 'Crime Rate', value: data.raw_data.crime.crime_per_1k.toFixed(1) + ' per 1k' },
        ]} />
        <MetricCard icon={<MapPin />} title="Points of Interest" items={[
          { label: 'Parks', value: String(data.raw_data.osm.parks) },
          { label: 'Transit', value: String(data.raw_data.osm.transit_stops) },
          { label: 'Grocery', value: String(data.raw_data.osm.grocery_stores) },
        ]} />
        <MetricCard icon={<Wind />} title="Environment" items={[
          { label: 'AQI', value: String(data.raw_data.air_quality.aqi) },
          { label: 'Category', value: data.raw_data.air_quality.category },
        ]} />
        <MetricCard icon={<Car />} title="Accessibility" items={[
          { label: 'Clinics', value: String(data.raw_data.osm.clinics) },
          { label: 'Transit Stops', value: String(data.raw_data.osm.transit_stops) },
        ]} />
      </div>

      {/* AI Narrative */}
      <div className="mt-20 bg-white p-12 rounded-[3rem] border border-black/5 shadow-sm">
        <h2 className="text-xs font-black text-black/30 uppercase tracking-[0.3em] mb-8 flex items-center">
          <Leaf className="h-4 w-4 mr-2 text-brand" />
          AI-Generated Civic Narrative
        </h2>
        {narrativeLoading ? (
          <div className="flex items-center space-x-3 text-black/40">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm font-medium">Generating insights...</span>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none text-black/70 leading-relaxed whitespace-pre-wrap">
            {narrative || 'Narrative will appear here once generated.'}
          </div>
        )}
      </div>
    </div>
  );
};

const MetricCard = ({ icon, title, items }: { icon: React.ReactNode; title: string; items: { label: string; value: string }[] }) => (
  <div className="bg-white p-8 rounded-[2rem] border border-black/5 hover:border-brand transition-all">
    <div className="flex items-center space-x-3 mb-6">
      <div className="p-2 bg-brand-light rounded-lg text-brand">{icon}</div>
      <h4 className="font-black text-xs uppercase tracking-widest">{title}</h4>
    </div>
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i}>
          <div className="text-[10px] font-black uppercase text-black/30 tracking-widest">{item.label}</div>
          <div className="font-bold text-sm">{item.value}</div>
        </div>
      ))}
    </div>
  </div>
);

export default Analysis;
