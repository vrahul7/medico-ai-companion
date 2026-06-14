import React from 'react';
import { Lock } from 'lucide-react';

export default function PremiumLock({ featureName }) {
    return (
        <div className="flex flex-col items-center justify-center p-12 text-center h-full bg-gray-50 rounded-lg border border-gray-200">
            <div className="p-4 bg-yellow-100 text-yellow-600 rounded-full mb-4">
                <Lock size={32} />
            </div>
            <h3 className="text-h3 text-gray-800 mb-2">{featureName} is a Premium Feature</h3>
            <p className="text-body text-gray-600 max-w-md mb-6">
                Upgrade to Medico Premium (₹99/month) to unlock unlimited access to {featureName} and more.
            </p>
            <button className="btn btn-primary bg-yellow-500 hover:bg-yellow-600 border-none">
                Unlock Now
            </button>
        </div>
    );
}
