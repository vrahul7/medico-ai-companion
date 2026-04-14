import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertTriangle, X } from 'lucide-react';
import PremiumLock from '../components/PremiumLock';

// Mock user state - Change to true to unlock
const IS_PREMIUM = false;

export default function LabAnalyzer() {
    const [file, setFile] = useState(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState(null);

    const handleFileUpload = (e) => {
        const uploadedFile = e.target.files[0];
        if (uploadedFile) {
            setFile(uploadedFile);
            setAnalyzing(true);

            // Simulate analysis delay
            setTimeout(() => {
                setAnalyzing(false);
                setResult({
                    patientName: "John Doe",
                    date: "2023-10-27",
                    abnormalities: [
                        { test: "Hemoglobin", value: "11.2 g/dL", range: "13.5-17.5", status: "Low", implication: "Anemia" },
                        { test: "WBC", value: "14,000 /uL", range: "4,500-11,000", status: "High", implication: "Infection/Inflammation" }
                    ],
                    summary: "The potential differential diagnoses include viral or bacterial infection, given the elevated WBC count. The low hemoglobin suggests mild anemia, which should be monitored."
                });
            }, 2000);
        }
    };

    const clearFile = () => {
        setFile(null);
        setResult(null);
    };

    return (
        <div className="flex flex-col gap-lg h-full">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-h2">Lab Report Analyzer</h2>
                    <p className="text-body text-gray-500">Upload PDF/JPEG reports for instant AI analysis.</p>
                </div>
                <span className="badge badge-premium">Premium Only</span>
            </div>

            {!IS_PREMIUM ? (
                <PremiumLock featureName="Lab Report Analyzer" />
            ) : !file ? (
                <div className="flex-1 card border-dashed border-2 border-gray-300 flex flex-col items-center justify-center gap-md bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer relative">
                    <input
                        type="file"
                        className="absolute inset-0 opacity-0 cursor-pointer"
                        onChange={handleFileUpload}
                        accept=".pdf,.jpg,.jpeg,.png"
                    />
                    <div className="p-4 rounded-full bg-blue-100 text-blue-600">
                        <UploadCloud size={48} />
                    </div>
                    <div className="text-center">
                        <p className="text-h3 text-gray-700">Click to upload or drag and drop</p>
                        <p className="text-small">PDF, JPG, or PNG (Max 10MB)</p>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col gap-lg animate-fade-in">
                    {/* File Preview Card */}
                    <div className="card flex items-center justify-between p-4">
                        <div className="flex items-center gap-md">
                            <div className="p-3 bg-red-100 text-red-500 rounded-md">
                                <FileText size={24} />
                            </div>
                            <div>
                                <p className="text-body font-bold">{file.name}</p>
                                <p className="text-small text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                            </div>
                        </div>
                        <button onClick={clearFile} className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
                            <X size={20} />
                        </button>
                    </div>

                    {analyzing ? (
                        <div className="card p-8 flex flex-col items-center justify-center gap-md text-center">
                            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                            <p className="text-h3 text-blue-600">Analyzing Report...</p>
                            <p className="text-small">Identifying abnormal values and correlating clinical data.</p>
                        </div>
                    ) : (
                        result && (
                            <div className="flex flex-col gap-md">
                                {/* Summary Card */}
                                <div className="card border-l-4 border-blue-500">
                                    <h3 className="text-h3 mb-2 text-blue-800">AI Assessment</h3>
                                    <p className="text-body leading-relaxed">{result.summary}</p>
                                </div>

                                {/* Abnormalities Table */}
                                <div className="card p-0 overflow-hidden">
                                    <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                                        <h3 className="text-body font-bold text-gray-700">Flagged Abnormalities</h3>
                                        <span className="text-small text-red-500 flex items-center gap-1">
                                            <AlertTriangle size={14} /> {result.abnormalities.length} issues found
                                        </span>
                                    </div>
                                    <table className="w-full text-left border-collapse">
                                        <thead>
                                            <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                                                <th className="p-4 font-medium">Test Name</th>
                                                <th className="p-4 font-medium">Result</th>
                                                <th className="p-4 font-medium">Reference Range</th>
                                                <th className="p-4 font-medium">Status</th>
                                                <th className="p-4 font-medium">Implication</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-100">
                                            {result.abnormalities.map((row, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50/50">
                                                    <td className="p-4 font-medium text-gray-800">{row.test}</td>
                                                    <td className="p-4 font-bold text-gray-900">{row.value}</td>
                                                    <td className="p-4 text-gray-500">{row.range}</td>
                                                    <td className="p-4">
                                                        <span className={`badge ${row.status === 'High' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                                                            {row.status}
                                                        </span>
                                                    </td>
                                                    <td className="p-4 text-blue-600 text-sm">{row.implication}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )
                    )}
                </div>
            )}
        </div>
    );
}
