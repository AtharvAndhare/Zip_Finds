
import React, { useState, Suspense } from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import { Search, BarChart3, Menu, X, Info, Github, Loader2 } from 'lucide-react';
import Home from './pages/Home';
import Analysis from './pages/Analysis';
import Compare from './pages/Compare';
import Dither from './Dither';

const App: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.length === 5) {
      navigate(`/analyze/${searchInput}`);
      setSearchInput('');
      setIsMenuOpen(false);
    }
  };

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div className="min-h-screen flex flex-col bg-transparent font-sans selection:bg-brand/20 relative">
      {/* Background Component wrapped in Suspense to prevent #525 errors */}
      <Suspense fallback={<div className="fixed inset-0 bg-[#f4f6f0] -z-10" />}>
        <Dither
          waveColor={[0.33, 0.42, 0.18]} // Olive Green approx
          disableAnimation={false}
          enableMouseInteraction
          mouseRadius={0.3}
          colorNum={4}
          waveAmplitude={0.3}
          waveFrequency={3}
          waveSpeed={0.05}
        />
      </Suspense>

      {/* Navigation Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-black/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-20 items-center">
            <div className="flex items-center space-x-2">
              <Link to="/" className="flex items-center space-x-2 group">
                <img src="/logo.png" alt="Zip Finds" className="h-20 w-auto group-hover:scale-105 transition-transform" />
                <span className="text-2xl font-black tracking-tighter text-black uppercase">
                  Zip Finds
                </span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-10">
              <Link 
                to="/" 
                className={`text-sm font-bold uppercase tracking-wider transition-colors ${location.pathname === '/' ? 'text-brand' : 'text-black hover:text-brand'}`}
              >
                Home
              </Link>
              <Link 
                to="/compare" 
                className={`text-sm font-bold uppercase tracking-wider transition-colors ${isActive('/compare') ? 'text-brand' : 'text-black hover:text-brand'}`}
              >
                Compare
              </Link>
              <form onSubmit={handleSearch} className="relative">
                <input
                  type="text"
                  placeholder="Analyze ZIP..."
                  className="pl-11 pr-4 py-2.5 bg-brand-light/50 border-none rounded-2xl text-sm font-medium focus:ring-2 focus:ring-brand w-48 transition-all focus:w-64 placeholder:text-brand/40"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  maxLength={5}
                />
                <Search className="absolute left-4 top-3 h-4 w-4 text-brand" />
              </form>
            </nav>

            {/* Mobile Toggle */}
            <div className="md:hidden flex items-center">
              <button 
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="text-black hover:text-brand p-2"
              >
                {isMenuOpen ? <X className="h-7 w-7" /> : <Menu className="h-7 w-7" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {isMenuOpen && (
          <div className="md:hidden bg-white/95 backdrop-blur-md border-b border-black/5 px-4 pt-2 pb-10 space-y-6">
            <Link to="/" onClick={() => setIsMenuOpen(false)} className="block text-2xl font-black text-black uppercase">Home</Link>
            <Link to="/compare" onClick={() => setIsMenuOpen(false)} className="block text-2xl font-black text-black uppercase">Compare</Link>
            <form onSubmit={handleSearch} className="relative pt-2">
              <input
                type="text"
                placeholder="Analyze ZIP..."
                className="w-full pl-12 pr-4 py-4 bg-brand-light border-none rounded-2xl text-lg focus:ring-2 focus:ring-brand"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                maxLength={5}
              />
              <Search className="absolute left-4 top-6.5 h-6 w-6 text-brand" />
            </form>
          </div>
        )}
      </header>

      {/* Maintenance Banner */}
      <div className="bg-black/90 backdrop-blur-sm text-white text-center py-3 px-6 text-sm font-medium z-40 relative">
        Data enrichment in progress. States ready: <span className="text-brand font-bold">NJ, MD, NY</span> | Coming soon: MA, AZ, WA, CA, TX
      </div>

      {/* Main Content Area */}
      <main className="flex-grow">
        {/* Fix: Added Loader2 import to support the spinner in Suspense fallback */}
        <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><Loader2 className="h-12 w-12 text-brand animate-spin" /></div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analyze/:zip" element={<Analysis />} />
            <Route path="/compare" element={<Compare />} />
          </Routes>
        </Suspense>
      </main>

      {/* Footer */}
      <footer className="bg-black text-white py-20 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-16 mb-16">
            <div>
              <div className="flex items-center space-x-3 text-white mb-6">
                <img src="/logo.png" alt="Zip Finds" className="h-18 w-auto brightness-0 invert" />
                <span className="text-xl font-black uppercase tracking-tighter">Zip Finds</span>
              </div>
              <p className="text-white/60 text-sm leading-loose">
                Synthesizing multi-modal civic datasets into actionable community insights. Built for citizens, researchers, and planners.
              </p>
            </div>
            <div>
              <h4 className="text-white font-black uppercase tracking-widest text-xs mb-6">Data Sources</h4>
              <ul className="text-sm space-y-3 text-white/60">
                <li className="hover:text-brand cursor-default">US Census Bureau</li>
                <li className="hover:text-brand cursor-default">HRSA (Health Resources)</li>
                <li className="hover:text-brand cursor-default">EPA AirNow Monitoring</li>
                <li className="hover:text-brand cursor-default">OpenStreetMap API</li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-black uppercase tracking-widest text-xs mb-6">Resources</h4>
              <div className="flex flex-col space-y-4">
                <a href="#" className="flex items-center space-x-2 text-white/60 hover:text-white transition-colors">
                  <Github className="h-5 w-5" /> <span>Open Source</span>
                </a>
                <a href="#" className="flex items-center space-x-2 text-white/60 hover:text-white transition-colors">
                  <Info className="h-5 w-5" /> <span>Methodology</span>
                </a>
              </div>
            </div>
          </div>
          <div className="pt-12 border-t border-white/5 text-center text-[10px] font-bold uppercase tracking-widest text-white/30">
            &copy; {new Date().getFullYear()} Zip Finds &bull; Civic Intelligence Reimagined
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
