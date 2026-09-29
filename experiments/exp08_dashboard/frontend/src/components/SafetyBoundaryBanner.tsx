import React from 'react';
import { AlertTriangle } from 'lucide-react';

export const SafetyBoundaryBanner: React.FC = () => {
  return (
    <aside aria-label="Safety boundary disclaimer" className="safety-boundary-banner">
      <AlertTriangle size={18} />
      <span>
        <strong>REGULATORY SAFETY NOTICE:</strong> Supervisory AI monitoring only. This system does NOT replace certified machine guarding, physical interlocks, emergency stops (E-stops), or safety-rated protective devices.
      </span>
    </aside>
  );
};
