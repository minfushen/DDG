import { Building2, MapPin, Calendar, User, Briefcase, Hash } from 'lucide-react';
import type { Enterprise } from '../../types';

interface EnterpriseHeaderProps {
  enterprise: Enterprise;
  children?: React.ReactNode;
}

export function EnterpriseHeader({ enterprise, children }: EnterpriseHeaderProps) {
  return (
    <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-lg">
            <Building2 className="w-7 h-7 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-800">{enterprise.name}</h2>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Hash className="w-3 h-3" />
                {enterprise.unifiedSocialCreditCode}
              </span>
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                {enterprise.legalPerson}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {enterprise.region}
              </span>
              <span className="flex items-center gap-1">
                <Briefcase className="w-3 h-3" />
                {enterprise.industry}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                成立于 {enterprise.establishedDate}
              </span>
            </div>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
