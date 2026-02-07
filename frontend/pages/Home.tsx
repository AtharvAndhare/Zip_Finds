
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, TrendingUp, Shield, Heart, Zap, Globe, Sparkles, BarChart3 } from 'lucide-react';

const Home: React.FC = () => {
  const [zipCode, setZipCode] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (zipCode.length === 5) {
      navigate(`/analyze/${zipCode}`);
    }
  };

  const features = [
    { icon: <Shield className="h-7 w-7 text-black" />, title: 'Safety Analysis', desc: 'Synthesized crime statistics and real-time safety indices.' },
    { icon: <Heart className="h-7 w-7 text-black" />, title: 'Health Infrastructure', desc: 'Critical care access and environmental quality monitoring.' },
    { icon: <Zap className="h-7 w-7 text-black" />, title: 'Digital Inclusion', desc: 'Broadband spectrum analysis and connectivity scoring.' },
    { icon: <TrendingUp className="h-7 w-7 text-black" />, title: 'Economic Pulse', desc: 'Income parity, housing cost burden, and opportunity.' }
  ];

  return (
    <div className="relative overflow-hidden bg-transparent">
      {/* Hero Section */}
      <section className="relative pt-32 pb-48 px-4 text-center">
        {/* Subtle Decorative Accents */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-black/[0.03] rounded-full -z-10"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-black/[0.05] rounded-full -z-10"></div>
        
        <div className="z-10 max-w-5xl mx-auto">
          <div className="flex flex-col items-center mb-10">
            <img src="/logo.png" alt="Zip Finds" className="h-48 w-auto mb-6" />
            <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full border border-black/10 bg-white/50 backdrop-blur-sm text-black text-xs font-black uppercase tracking-widest">
              <Sparkles className="h-3 w-3 text-brand" />
              <span>Understand Any Neighborhood Using ZipFinds</span>
            </div>
          </div>
          <h1 className="text-6xl md:text-9xl font-black text-black mb-8 tracking-tighter uppercase leading-[0.9]">
            Civic Intelligence <br/><span className="text-brand">for Everyone.</span>
          </h1>
          <p className="text-xl text-black/60 mb-16 max-w-2xl mx-auto leading-relaxed font-medium">
            Deconstruct the DNA of any US Zip Code. From infrastructure health to environmental stability, we translate millions of data points into actionable grades.
          </p>

          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row items-center justify-center gap-2 max-w-2xl mx-auto p-2 bg-black rounded-[2.5rem] shadow-2xl shadow-brand/20">
            <div className="relative flex-grow w-full">
              <input
                type="text"
                placeholder="Enter 5-digit ZIP Code"
                className="w-full pl-8 pr-4 py-6 bg-transparent text-white text-xl font-bold placeholder:text-white/30 border-none focus:ring-0 outline-none"
                value={zipCode}
                onChange={(e) => setZipCode(e.target.value.replace(/\D/g, '').slice(0, 5))}
                required
              />
            </div>
            <button
              type="submit"
              className="w-full sm:w-auto px-12 py-5 bg-brand text-white font-black uppercase tracking-widest rounded-[2rem] hover:bg-white hover:text-black transition-all transform active:scale-95 whitespace-nowrap"
            >
              Analyze
            </button>
          </form>
          
          <div className="mt-20 flex flex-wrap justify-center gap-10 text-[10px] font-black uppercase tracking-[0.2em] text-black/40">
            <div className="flex items-center space-x-2 border-b border-black/10 pb-1"><Globe className="h-4 w-4" /> <span>National Coverage</span></div>
            <div className="flex items-center space-x-2 border-b border-black/10 pb-1"><BarChart3 className="h-4 w-4" /> <span>8+ Key Vectors</span></div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-32 border-t border-black/5 bg-white/30 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-end mb-20 gap-8">
            <div className="max-w-2xl">
              <h2 className="text-4xl font-black text-black mb-4 uppercase tracking-tighter">Multi-Vector Neighborhood Profiling</h2>
              <p className="text-black/50 font-medium">We aggregate high-fidelity data from US Census, EPA, HRSA, and OSM to provide the most complete civic portrait available.</p>
            </div>
            <div className="h-1 w-24 bg-brand"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {features.map((f, i) => (
              <div key={i} className="group p-10 bg-white/60 backdrop-blur-md border border-black/5 hover:border-brand/40 transition-all rounded-[2rem] hover:bg-brand-light/80">
                <div className="mb-6 p-4 bg-brand-light rounded-2xl w-fit group-hover:bg-white transition-colors">{f.icon}</div>
                <h3 className="text-xl font-black text-black mb-4 uppercase tracking-tight">{f.title}</h3>
                <p className="text-black/50 text-sm leading-relaxed font-medium">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-40 bg-black overflow-hidden relative">
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand opacity-10 blur-[150px]"></div>
        <div className="max-w-7xl mx-auto px-4 text-center relative z-10">
          <h2 className="text-4xl md:text-6xl font-black text-white mb-12 uppercase tracking-tighter">Strategic relocation <br/>starts with data.</h2>
          <button 
            onClick={() => navigate('/compare')}
            className="group px-16 py-6 bg-brand text-white font-black uppercase tracking-widest rounded-full hover:bg-white hover:text-black transition-all flex items-center mx-auto"
          >
            Open Comparison Tool
            <TrendingUp className="ml-3 h-5 w-5 transform group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
          </button>
        </div>
      </section>
    </div>
  );
};

export default Home;
