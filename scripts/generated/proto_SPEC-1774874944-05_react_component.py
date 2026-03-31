import React, { useState, useEffect } from 'react';

interface MotionType {
  value: string;
  label: string;
  type: 'translate' | 'scale' | 'rotate' | 'shake' | 'none';
  params: Record<string, unknown>;
}

interface ShotType {
  value: string;
  label: string;
}

const API_BASE_URL = 'http://47.121.27.3:8000';

const MotionTypeCard: React.FC<{ motion: MotionType }> = ({ motion }) => {
  const typeColors: Record<string, string> = {
    translate: 'bg-blue-100 text-blue-800 border-blue-300',
    scale: 'bg-green-100 text-green-800 border-green-300',
    rotate: 'bg-orange-100 text-orange-800 border-orange-300',
    shake: 'bg-red-100 text-red-800 border-red-300',
    none: 'bg-gray-100 text-gray-800 border-gray-300',
  };

  const colorClass = typeColors[motion.type] || typeColors.none;

  return (
    <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900">{motion.label}</h3>
        <span className={`px-2 py-1 text-xs font-medium rounded-full border ${colorClass}`}>
          {motion.type}
        </span>
      </div>
      <div className="mt-2">
        <span className="text-xs text-gray-500 uppercase tracking-wide">参数预览</span>
        <pre className="mt-1 text-xs bg-gray-50 p-2 rounded border border-gray-200 overflow-x-auto">
          {JSON.stringify(motion.params, null, 2)}
        </pre>
      </div>
    </div>
  );
};

const ShotTypeCard: React.FC<{ shot: ShotType; onCopy: (value: string) => void }> = ({ shot, onCopy }) => {
  const handleCopy = () => {
    onCopy(shot.value);
  };

  return (
    <div
      onClick={handleCopy}
      className="bg-white rounded-lg shadow-md p-4 border border-gray-200 hover:shadow-lg hover:border-blue-300 transition-all cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <p className="text-gray-900 font-medium">{shot.label}</p>
        <svg
          className="w-4 h-4 text-gray-400 hover:text-blue-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      </div>
    </div>
  );
};

const SkeletonCard: React.FC = () => (
  <div className="bg-white rounded-lg shadow-md p-4 border border-gray-200 animate-pulse">
    <div className="flex items-start justify-between mb-3">
      <div className="h-6 bg-gray-200 rounded w-24"></div>
      <div className="h-5 bg-gray-200 rounded-full w-16"></div>
    </div>
    <div className="mt-2">
      <div className="h-3 bg-gray-200 rounded w-16 mb-1"></div>
      <div className="h-12 bg-gray-100 rounded border border-gray-200"></div>
    </div>
  </div>
);

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="flex flex-col items-center justify-center py-12 text-gray-500">
    <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
    <p className="text-lg">{message}</p>
  </div>
);

const ErrorState: React.FC<{ onRetry: () => void }> = ({ onRetry }) => (
  <div className="flex flex-col items-center justify-center py-12">
    <svg className="w-16 h-16 mb-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
    <p className="text-lg text-gray-700 mb-4">加载失败,请重试</p>
    <button
      onClick={onRetry}
      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
    >
      重试
    </button>
  </div>
);

const OptionsConfigPage: React.FC = () => {
  const [motionTypes, setMotionTypes] = useState<MotionType[]>([]);
  const [shotTypes, setShotTypes] = useState<ShotType[]>([]);
  const [motionLoading, setMotionLoading] = useState(true);
  const [shotLoading, setShotLoading] = useState(true);
  const [motionError, setMotionError] = useState(false);
  const [shotError, setShotError] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  const fetchMotionTypes = async () => {
    setMotionLoading(true);
    setMotionError(false);
    try {
      const response = await fetch(`${API_BASE_URL}/api/options/motion-types`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setMotionTypes(data);
    } catch {
      setMotionError(true);
    } finally {
      setMotionLoading(false);
    }
  };

  const fetchShotTypes = async () => {
    setShotLoading(true);
    setShotError(false);
    try {
      const response = await fetch(`${API_BASE_URL}/api/options/shot-types`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setShotTypes(data);
    } catch {
      setShotError(true);
    } finally {
      setShotLoading(false);
    }
  };

  useEffect(() => {
    fetchMotionTypes();
    fetchShotTypes();
  }, []);

  const handleCopyValue = (value: string) => {
    navigator.clipboard.writeText(value).then(() => {
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">选项配置</h1>
          <p className="mt-2 text-gray-600">管理运动类型、镜头类型和动态效果选项</p>
        </header>

        <section className="mb-12">
          <div className="flex items-center mb-6">
            <svg className="w-6 h-6 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-2xl font-semibold text-gray-900">运动类型</h2>
          </div>

          {motionLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : motionError ? (
            <ErrorState onRetry={fetchMotionTypes} />
          ) : motionTypes.length === 0 ? (
            <EmptyState message="暂无选项数据" />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {motionTypes.map((motion) => (
                <MotionTypeCard key={motion.value} motion={motion} />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center mb-6">
            <svg className="w-6 h-6 text-purple-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <h2 className="text-2xl font-semibold text-gray-900">镜头类型</h2>
          </div>

          {shotLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-lg shadow-md p-4 border border-gray-200 animate-pulse">
                  <div className="flex items-center justify-between">
                    <div className="h-5 bg-gray-200 rounded w-48"></div>
                    <div className="h-4 w-4 bg-gray-200 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : shotError ? (
            <ErrorState onRetry={fetchShotTypes} />
          ) : shotTypes.length === 0 ? (
            <EmptyState message="暂无选项数据" />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {shotTypes.map((shot) => (
                <ShotTypeCard key={shot.value} shot={shot} onCopy={handleCopyValue} />
              ))}
            </div>
          )}
        </section>

        {copySuccess && (
          <div className="fixed bottom-6 right-6 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg animate-fade-in">
            已复制到剪贴板
          </div>
        )}
      </div>
    </div>
  );
};

export default OptionsConfigPage;