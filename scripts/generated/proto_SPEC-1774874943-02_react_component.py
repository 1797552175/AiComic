import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = 'http://47.121.27.3:8000';

interface Scene {
  id: string;
  location: string;
  shots: any[];
}

interface ParseResult {
  project_id: string;
  scenes: Scene[];
  characters: any[];
  warnings: string[];
}

interface StyleSelectorProps {
  value: string;
  onChange: (style: string) => void;
}

const StyleSelector: React.FC<StyleSelectorProps> = ({ value, onChange }) => {
  const styles = [
    { value: 'anime', label: 'Anime' },
    { value: 'realistic', label: 'Realistic' },
    { value: 'cyberpunk', label: 'Cyberpunk' },
    { value: 'ink', label: 'Ink' },
    { value: 'bw', label: 'B&W' },
  ];

  return (
    <div className="flex flex-wrap gap-4 mb-4">
      {styles.map((s) => (
        <label
          key={s.value}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 cursor-pointer transition-all ${
            value === s.value
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
          }`}
        >
          <input
            type="radio"
            name="style"
            value={s.value}
            checked={value === s.value}
            onChange={() => onChange(s.value)}
            className="sr-only"
          />
          <span className="font-medium">{s.label}</span>
        </label>
      ))}
    </div>
  );
};

interface ScriptTextareaProps {
  value: string;
  onChange: (value: string) => void;
}

const ScriptTextarea: React.FC<ScriptTextareaProps> = ({ value, onChange }) => {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={'支持【场景X:地点·时间】格式,例如:\n\n【场景1:教室·白天】\n小明走进教室,看到小红在窗边读书。\n\n【场景2:操场·课间】\n操场上同学们在打篮球。'}
      className="w-full p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      rows={15}
    />
  );
};

interface ParseButtonProps {
  onClick: () => void;
  loading: boolean;
}

const ParseButton: React.FC<ParseButtonProps> = ({ onClick, loading }) => {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
    >
      {loading ? (
        <>
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>解析中...</span>
        </>
      ) : (
        <span>一键解析</span>
      )}
    </button>
  );
};

interface ParseResultPanelProps {
  result: ParseResult;
}

const ParseResultPanel: React.FC<ParseResultPanelProps> = ({ result }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">解析结果</h2>

      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">角色数量:</span>
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
            {result.characters?.length || 0}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-600">场景数量:</span>
          <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
            {result.scenes?.length || 0}
          </span>
        </div>
      </div>

      {result.warnings && result.warnings.length > 0 && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h4 className="text-sm font-semibold text-yellow-800 mb-2">警告</h4>
          <ul className="text-sm text-yellow-700 list-disc list-inside space-y-1">
            {result.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">场景预览</h4>
        <div className="space-y-2">
          {result.scenes?.map((scene, index) => (
            <div
              key={scene.id || index}
              className="p-4 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-between"
            >
              <span className="font-medium text-gray-800">{scene.location}</span>
              <span className="text-sm text-gray-500 bg-white px-2 py-1 rounded">
                {scene.shots?.length || 0} 个分镜
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const ScriptEditorPage: React.FC = () => {
  const navigate = useNavigate();
  const params = useParams();
  const projectId = params.id || '';

  const [scriptText, setScriptText] = useState('');
  const [style, setStyle] = useState('anime');
  const [loading, setLoading] = useState(false);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    if (!scriptText.trim()) {
      setError('请输入剧本内容');
      return;
    }

    if (!projectId) {
      setError('项目ID不存在');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/projects/${projectId}/parse-script`,
        {
          script_text: scriptText,
          style: style,
        }
      );

      setParseResult(response.data);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || err.message || '解析失败,请重试';
      setError(errorMessage);
      setParseResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/projects')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="返回项目列表"
            >
              <svg
                className="w-5 h-5 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <h1 className="text-2xl font-bold text-gray-900">剧本编辑</h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">剧本内容</h2>

          <StyleSelector value={style} onChange={setStyle} />

          <div className="mb-4">
            <ScriptTextarea value={scriptText} onChange={setScriptText} />
          </div>

          <div className="flex items-center gap-4">
            <ParseButton onClick={handleParse} loading={loading} />

            {error && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>{error}</span>
              </div>
            )}
          </div>
        </div>

        {parseResult && <ParseResultPanel result={parseResult} />}
      </main>
    </div>
  );
};

export default ScriptEditorPage;