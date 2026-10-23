import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Incident } from '../types';
import { AlertTriangle, Layers, Navigation, RefreshCw } from 'lucide-react';

interface Props {
  incidents: Incident[];
  selectedIncidentId?: string | null;
  onSelectIncident?: (id: string) => void;
}

type TileSource = 'carto_dark' | 'carto_voyager' | 'osm';

const TILE_PROVIDERS: Record<TileSource, { name: string; url: string; attribution: string; subdomains: string; maxZoom: number }> = {
  carto_dark: {
    name: 'Dark Matter (CARTO)',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  },
  carto_voyager: {
    name: 'Voyager (CARTO)',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  },
  osm: {
    name: 'OpenStreetMap (Standard)',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    subdomains: 'abc',
    maxZoom: 19,
  },
};

export const GroundedMap: React.FC<Props> = ({
  incidents,
  selectedIncidentId,
  onSelectIncident,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markersGroupRef = useRef<L.FeatureGroup | null>(null);
  const [activeTileSource, setActiveTileSource] = useState<TileSource>('carto_dark');
  const [mapLoaded, setMapLoaded] = useState(false);

  const groundedIncidents = incidents.filter(
    (inc) => inc.has_grounded_coordinates && inc.latitude && inc.longitude
  );

  // 1. Initialize map once
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const defaultCenter: [number, number] = [19.035, 72.85]; // Mumbai default
      const map = L.map(mapContainerRef.current, {
        center: defaultCenter,
        zoom: 12,
        zoomControl: true,
      });

      const provider = TILE_PROVIDERS[activeTileSource];
      const tileLayer = L.tileLayer(provider.url, {
        attribution: provider.attribution,
        maxZoom: provider.maxZoom,
        subdomains: provider.subdomains,
      }).addTo(map);

      tileLayerRef.current = tileLayer;
      const markersGroup = L.featureGroup().addTo(map);
      markersGroupRef.current = markersGroup;
      mapInstanceRef.current = map;
      setMapLoaded(true);

      // Force recalculate dimensions once DOM has rendered
      setTimeout(() => {
        map.invalidateSize();
      }, 200);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        tileLayerRef.current = null;
        markersGroupRef.current = null;
        setMapLoaded(false);
      }
    };
  }, []);

  // 2. Tile layer change handler
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const provider = TILE_PROVIDERS[activeTileSource];

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }

    const newLayer = L.tileLayer(provider.url, {
      attribution: provider.attribution,
      maxZoom: provider.maxZoom,
      subdomains: provider.subdomains,
    }).addTo(map);

    tileLayerRef.current = newLayer;
  }, [activeTileSource]);

  // 3. Update markers and bounds
  useEffect(() => {
    if (!mapInstanceRef.current || !markersGroupRef.current) return;
    const map = mapInstanceRef.current;
    const markersGroup = markersGroupRef.current;

    markersGroup.clearLayers();

    groundedIncidents.forEach((inc) => {
      const isSelected = inc.id === selectedIncidentId;
      const isCritical = inc.approved_priority === 'critical';

      const customIcon = L.divIcon({
        className: 'custom-map-marker',
        html: `
          <div style="
            width: 32px;
            height: 32px;
            background: ${isCritical ? '#FF5C68' : '#FF2DA8'};
            border: 2px solid ${isSelected ? '#D4FF3F' : '#FFFFFF'};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 ${isSelected ? '16px #D4FF3F' : '10px rgba(255,45,168,0.5)'};
            cursor: pointer;
            transition: all 0.2s ease;
          ">
            <span style="font-size: 11px; font-weight: 800; color: #000; font-family: monospace;">
              ${inc.category === 'waterlogging' ? 'W' : 'T'}
            </span>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([inc.latitude!, inc.longitude!], { icon: customIcon })
        .bindPopup(`
          <div style="background: #151515; color: #fff; padding: 6px; font-family: sans-serif; min-width: 180px;">
            <div style="font-weight: bold; font-size: 13px; color: #FF2DA8; margin-bottom: 4px;">
              ${inc.title}
            </div>
            <div style="font-size: 11px; color: #A7A7A7; margin-bottom: 4px;">
              ${inc.location_name}
            </div>
            <div style="font-size: 10px; font-family: monospace; color: #D4FF3F;">
              GROUNDED: [${inc.latitude?.toFixed(4)}, ${inc.longitude?.toFixed(4)}]
            </div>
            <div style="font-size: 11px; margin-top: 6px; text-transform: uppercase; font-weight: bold; color: ${isCritical ? '#FF5C68' : '#F5B942'};">
              PRIORITY: ${inc.approved_priority}
            </div>
          </div>
        `);

      marker.on('click', () => {
        if (onSelectIncident) {
          onSelectIncident(inc.id);
        }
      });

      markersGroup.addLayer(marker);
    });

    if (groundedIncidents.length > 0) {
      const bounds = markersGroup.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds.pad(0.3));
      }
    }

    // Always trigger resize when markers reload
    map.invalidateSize();
  }, [groundedIncidents.length, selectedIncidentId, mapLoaded]);

  const handleRecenter = () => {
    if (!mapInstanceRef.current || !markersGroupRef.current) return;
    const bounds = markersGroupRef.current.getBounds();
    if (bounds.isValid()) {
      mapInstanceRef.current.fitBounds(bounds.pad(0.3));
    } else {
      mapInstanceRef.current.setView([19.035, 72.85], 12);
    }
    mapInstanceRef.current.invalidateSize();
  };

  return (
    <div className="relative w-full h-full min-h-[440px] bg-[#151515] rounded-xl overflow-hidden border border-[#282828] flex flex-col">
      {/* Top Banner on Map */}
      <div className="absolute top-3 left-3 z-[400] flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0B0B0B]/90 backdrop-blur border border-[#282828] text-xs font-mono shadow-lg">
        <span className="w-2 h-2 rounded-full bg-[#D4FF3F] animate-pulse" />
        <span className="text-white font-semibold">Grounded Coordinate Surface</span>
        <span className="text-[#A7A7A7]">({groundedIncidents.length} Grounded Points)</span>
      </div>

      {/* Layer & Control Toolbar (Top Right) */}
      <div className="absolute top-3 right-3 z-[400] flex items-center gap-1.5 p-1 rounded-lg bg-[#0B0B0B]/90 backdrop-blur border border-[#282828] text-xs shadow-lg">
        <select
          value={activeTileSource}
          onChange={(e) => setActiveTileSource(e.target.value as TileSource)}
          aria-label="Map Tile Layer"
          className="bg-[#181818] text-[#D4FF3F] text-[11px] font-mono px-2 py-1 rounded border border-[#333] focus:outline-none focus:border-[#FF2DA8] cursor-pointer"
        >
          <option value="carto_dark">CARTO Dark</option>
          <option value="carto_voyager">CARTO Voyager</option>
          <option value="osm">OpenStreetMap</option>
        </select>

        <button
          onClick={handleRecenter}
          title="Recenter Map"
          className="p-1 rounded bg-[#181818] hover:bg-[#252525] text-white border border-[#333] transition-colors"
        >
          <Navigation className="w-3.5 h-3.5 text-[#FF2DA8]" />
        </button>
      </div>

      {/* Leaflet Container */}
      <div
        ref={mapContainerRef}
        className="w-full flex-1 z-0 min-h-[350px]"
        style={{ minHeight: '350px' }}
      />

      {/* Ungrounded Notice Bar */}
      {incidents.some((i) => !i.has_grounded_coordinates) && (
        <div className="bg-[#101010] border-t border-[#282828] px-4 py-2 flex items-center justify-between text-xs font-mono text-[#A7A7A7] z-[400]">
          <div className="flex items-center gap-2 text-[#F5B942]">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Reports with ungrounded/ambiguous locations are isolated to list view to prevent hallucinated coordinates.</span>
          </div>
        </div>
      )}
    </div>
  );
};
