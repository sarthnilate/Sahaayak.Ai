import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Incident } from '../types';
import { MapPin, AlertTriangle } from 'lucide-react';

interface Props {
  incidents: Incident[];
  selectedIncidentId?: string | null;
  onSelectIncident?: (id: string) => void;
}

export const GroundedMap: React.FC<Props> = ({
  incidents,
  selectedIncidentId,
  onSelectIncident
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<{ [key: string]: L.Marker }>({});

  const groundedIncidents = incidents.filter(
    (inc) => inc.has_grounded_coordinates && inc.latitude && inc.longitude
  );

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Default center around Mumbai where simulated rainfall reports are situated
      const defaultCenter: [number, number] = [19.035, 72.85];
      const map = L.map(mapContainerRef.current, {
        center: defaultCenter,
        zoom: 12,
        zoomControl: true,
      });

      // CartoDB Dark Matter tiles for dark-first aesthetic
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CartoDB</a>',
        maxZoom: 19,
        subdomains: 'abcd',
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;

    // Clear old markers
    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};

    // Add markers for grounded coordinates
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
        .addTo(map)
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

      markersRef.current[inc.id] = marker;
    });

    // Fit bounds if markers exist
    if (groundedIncidents.length > 0) {
      const group = L.featureGroup(Object.values(markersRef.current));
      map.fitBounds(group.getBounds().pad(0.3));
    }

  }, [groundedIncidents.length, selectedIncidentId]);

  return (
    <div className="relative w-full h-full min-h-[380px] bg-[#151515] rounded-xl overflow-hidden border border-[#282828] flex flex-col">
      {/* Top Banner on Map */}
      <div className="absolute top-3 left-3 z-[400] flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0B0B0B]/90 backdrop-blur border border-[#282828] text-xs font-mono">
        <span className="w-2 h-2 rounded-full bg-[#D4FF3F] animate-pulse" />
        <span className="text-white font-semibold">Grounded Coordinate Surface</span>
        <span className="text-[#A7A7A7]">({groundedIncidents.length} Grounded Points)</span>
      </div>

      {/* Leaflet Container */}
      <div ref={mapContainerRef} className="w-full flex-1 z-0" />

      {/* Ungrounded Notice Bar */}
      {incidents.some((i) => !i.has_grounded_coordinates) && (
        <div className="bg-[#101010] border-t border-[#282828] px-4 py-2 flex items-center justify-between text-xs font-mono text-[#A7A7A7]">
          <div className="flex items-center gap-2 text-[#F5B942]">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Reports with ungrounded/ambiguous locations are isolated to list view to prevent hallucinated coordinates.</span>
          </div>
        </div>
      )}
    </div>
  );
};
