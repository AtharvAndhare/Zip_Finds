
import React, { useState } from 'react';
import Plot from 'react-plotly.js';
import { 
  Plus, X, Loader2, AlertCircle, 
  ChevronRight, BarChart4, Scaling, Check
} from 'lucide-react';
import { compareZips } from '../services/api';
import { ZipAnalysis } from '../types';

const Compare: React.FC = () => {
  const [zipInputs, setZipInputs] = useState<string[]>(['', '']);
  const [results, setResults] = useState<ZipAnalysis[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addInput = () => {
    if (zipInputs.length < 4) setZipInputs([...zipInputs, '']);
  };

  const removeInput = (index: number) => {
    const next = [...zipInputs];
    next.splice(index, 1);
    setZipInputs(next);
  };

  const updateInput = (index: number, val: string) => {
    const next = [...zipInputs];
    next[index] = val.replace(/\D/g, '').slice(0, 5);
    setZipInputs(next);
  };

  const handleCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    const validZips = zipInputs.filter(z => z.length === 5);
    if (validZips.length < 2) {
      setError('Please enter at least 2 valid zip codes to compare.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await compareZips(validZips);
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Comparison failure. API server status unknown.');
    } finally {
      setLoading(false);
    }
  };

  const scoreCategories = [
    'Safety', 'Health', 'Education', 'EconomicOpportunity', 
    'HousingAffordability', 'DigitalAccess', 'Environment', 'Accessibility'
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-20">
      <div className="text-center mb-20">
        <h1 className="text-6xl font-black text-black mb-6 uppercase tracking-tighter">Neighborhood <span className="text-brand">Versus</span></h1>
        <p className="text-black/50 font-medium max-w-xl mx-auto">Cross-examine up to 4 locations side-by-side using standardized civic metrics.</p>
      </div>

      <div className="max-w-4xl mx-auto bg-white p-12 rounded-[3.5rem] border border-black/5 shadow-2xl mb-24">
        <form onSubmit={handleCompare}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-10">
            {zipInputs.map((zip, i) => (
              <div key={i} className="relative group">
                <input
                  type="text"
                  placeholder={`Location ${i + 1} ZIP`}
                  className="w-full px-8 py-5 rounded-3xl bg-brand-light border-none focus:ring-4 focus:ring-brand/10 outline-none text-2xl font-black placeholder:text-brand/20"
                  value={zip}
                  onChange={(e) => updateInput(i, e.target.value)}
                  maxLength={5}
                />
                {zipInputs.length > 2 && (
                  <button 
                    type="button"
                    onClick={() => removeInput(i)}
                    className="absolute right-4 top-5 text-brand/20 hover:text-black transition-colors"
                  >
                    <X className="h-6 w-6" />
                  </button>
                )}
              </div>
            ))}
            {zipInputs.length < 4 && (
              <button
                type="button"
                onClick={addInput}
                className="flex items-center justify-center border-4 border-dashed border-black/5 rounded-3xl py-5 text-black/20 hover:border-brand hover:text-brand transition-all font-black uppercase tracking-widest text-xs"
              >
                <Plus className="h-5 w-5 mr-3" /> Append ZIP
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-6 bg-black text-white font-black uppercase tracking-[0.3em] rounded-3xl hover:bg-brand disabled:opacity-30 shadow-2xl flex items-center justify-center transition-all transform active:scale-95"
          >
            {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : 'Launch Cross-Analysis'}
          </button>
          {error && (
            <div className="mt-6 flex items-center space-x-2 text-black text-[10px] font-black uppercase tracking-widest justify-center">
              <AlertCircle className="h-4 w-4 text-brand" />
              <span>{error}</span>
            </div>
          )}
        </form>
      </div>

      {results && results.length > 0 && (
        <div className="space-y-24">
          
          {/* Comparison Summary Cards */}
          <div className={`grid grid-cols-1 md:grid-cols-${results.length} gap-8`}>
            {results.map((res, i) => (
              <div key={i} className="bg-white p-12 rounded-[3.5rem] border border-black/5 shadow-sm relative overflow-hidden transition-transform hover:-translate-y-2">
                <div className="absolute top-0 left-0 w-full h-3 bg-brand opacity-20" />
                <h3 className="text-4xl font-black text-black mb-1 uppercase tracking-tighter">{res.zip_code}</h3>
                <p className="text-[10px] text-black/30 font-black uppercase tracking-[0.3em] mb-10">Civic Index Summary</p>
                <div className="flex items-end space-x-2 mb-10">
                  <span className="text-7xl font-black text-brand leading-none">{res.scores.OverallCivicScore}</span>
                  <span className="text-black/10 mb-2 text-2xl font-black">/100</span>
                </div>
                <div className="space-y-4">
                   {scoreCategories.slice(0, 4).map((cat, j) => (
                     <div key={j} className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest">
                       <span className="text-black/30">{(cat.replace(/([A-Z])/g, ' $1').trim())}</span>
                       <span className="text-black">{(res.scores as any)[cat]}</span>
                     </div>
                   ))}
                </div>
              </div>
            ))}
          </div>

          {/* Combined Bar Chart */}
          <div className="bg-white p-16 rounded-[4rem] border border-black/5 shadow-sm overflow-x-auto">
            <h3 className="text-xs font-black text-black/20 uppercase tracking-[0.4em] mb-12 flex items-center">
              <BarChart4 className="h-4 w-4 mr-3 text-brand" />
              Comparative Metrics Matrix
            </h3>
            <div className="min-w-[700px]">
              <Plot
                data={results.map((res, i) => ({
                  x: scoreCategories.map(s => s.replace(/([A-Z])/g, ' $1').trim().toUpperCase()),
                  y: scoreCategories.map(s => (res.scores as any)[s]),
                  name: res.zip_code,
                  type: 'bar',
                  marker: {
                    color: i === 0 ? '#000000' : i === 1 ? '#556b2f' : i === 2 ? '#f4f6f0' : '#415224',
                    line: { width: 0 }
                  }
                }))}
                layout={{
                  barmode: 'group',
                  height: 500,
                  margin: { l: 40, r: 20, t: 10, b: 120 },
                  xaxis: { tickfont: { size: 9, family: 'Inter', color: '#000', weight: '900' } },
                  yaxis: { range: [0, 100], gridcolor: '#f8f8f8', tickfont: { size: 10, family: 'Inter', color: '#ccc' } },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  legend: { orientation: 'h', x: 0.5, xanchor: 'center', y: -0.3, font: { family: 'Inter', weight: '900', size: 12 } }
                }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>
          </div>

          {/* Head-to-Head Table */}
          <div className="bg-white rounded-[4rem] border border-black/5 shadow-sm overflow-hidden">
             <div className="p-12 border-b border-black/5 flex items-center">
               <Scaling className="h-6 w-6 mr-4 text-brand" />
               <h3 className="text-xs font-black text-black uppercase tracking-[0.3em]">Precision Attribute Mapping</h3>
             </div>
             <div className="overflow-x-auto">
               <table className="w-full text-left">
                 <thead>
                   <tr className="bg-brand-light/30">
                     <th className="px-12 py-6 text-[10px] font-black text-black/40 uppercase tracking-[0.3em]">Attribute</th>
                     {results.map((res, i) => (
                       <th key={i} className="px-12 py-6 font-black text-black text-sm uppercase tracking-tighter">{res.zip_code}</th>
                     ))}
                   </tr>
                 </thead>
                 <tbody className="divide-y divide-black/5">
                   <MetricRow label="Household Income" path="raw_data.census.median_income" results={results} formatter={(v) => `$${v.toLocaleString()}`} />
                   <MetricRow label="Population" path="raw_data.census.resident_base" results={results} formatter={(v) => v.toLocaleString()} />
                   <MetricRow label="Housing Rent Cost" path="raw_data.housing.median_rent" results={results} formatter={(v) => `$${v.toLocaleString()}`} />
                   <MetricRow label="Rent-to-Income" path="raw_data.housing.rent_to_income" results={results} formatter={(v) => v > 1 ? `${v.toFixed(1)}%` : `${(v * 100).toFixed(1)}%`} />
                   <MetricRow label="Edu Attainment" path="raw_data.census.bachelors_rate" results={results} formatter={(v) => v > 1 ? `${v.toFixed(1)}%` : `${(v * 100).toFixed(1)}%`} />
                   <MetricRow label="Broadband Coverage" path="raw_data.broadband.broadband_pct" results={results} formatter={(v) => v > 1 ? `${v.toFixed(1)}%` : `${(v * 100).toFixed(1)}%`} />
                   <MetricRow label="Air Quality (AQI)" path="raw_data.air_quality.aqi" results={results} />
                   <MetricRow label="Crime Rate" path="raw_data.crime.crime_per_1k" results={results} formatter={(v) => v.toFixed(1)} />
                   <MetricRow label="Hospitals" path="raw_data.health.hospitals" results={results} />
                   <MetricRow label="Parks" path="raw_data.osm.parks" results={results} />
                   <MetricRow label="Transit Stops" path="raw_data.osm.transit_stops" results={results} />
                 </tbody>
               </table>
             </div>
          </div>
        </div>
      )}
    </div>
  );
};

const MetricRow = ({ label, path, results, formatter }: { label: string, path: string, results: ZipAnalysis[], formatter?: (v: any) => string }) => {
  const getValue = (obj: any, path: string) => {
    return path.split('.').reduce((acc, part) => acc && acc[part], obj);
  };

  const values = results.map(r => getValue(r, path));
  const max = Math.max(...values);
  const min = Math.min(...values);
  
  const isLowerBetter = label.toLowerCase().includes('crime') || label.toLowerCase().includes('aqi') || label.toLowerCase().includes('rent');

  return (
    <tr className="hover:bg-brand-light/20 transition-colors group">
      <td className="px-12 py-8 text-[10px] text-black/40 font-black uppercase tracking-widest">{label}</td>
      {values.map((v, i) => {
        const isBest = isLowerBetter ? v === min : v === max;
        return (
          <td key={i} className={`px-12 py-8 text-sm font-bold ${isBest ? 'text-brand' : 'text-black'}`}>
            <div className="flex items-center">
              {formatter ? formatter(v) : v}
              {isBest && <Check className="h-4 w-4 ml-3 text-brand" />}
            </div>
          </td>
        );
      })}
    </tr>
  );
};

export default Compare;
