import React, { useState, useEffect } from 'react';
import AppLayout from './AppLayout';

interface Project {
  id: string;
  user_id: string;
  title: string;
  status: 'draft' | 'generating' | 'completed';
  style: 'anime' | 'realistic' | 'cyberpunk' | 'ink' | 'bw';
  thumbnail?: string;
  created_at: string;
  updated_at: string;
  settings?: {
    style?: string;
    [key: string]: any;
  };
}

interface CreateProjectRequest {
  user_id: string;
  title: string;
  settings: {
    style: string;
  };
}

const API_BASE_URL = 'http://47.121.27.3:8000';

const styleLabels: Record<string, string> = {
  anime: '动漫',
  realistic: '写实',
  cyberpunk: '赛博朋克',
  ink: '水墨',
  bw: '黑白',
};

const statusLabels: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  generating: { label: '生成中', color: 'bg-yellow-100 text-yellow-700' },
  completed: { label: '已完成', color: 'bg-green-100 text-green-700' },
};

const ProjectCard: React.FC<{
  project: Project;
  onEdit: (project: Project) => void;
  onDelete: (id: string) => void;
  onClick: (project: Project) => void;
}> = ({ project, onEdit, onDelete, onClick }) => {
  const [showMenu, setShowMenu] = useState(false);
  const status = statusLabels[project.status] || statusLabels.draft;

  return (
    <div className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">
      <div className="relative cursor-pointer" onClick={() => onClick(project)}>
        <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
          {project.thumbnail ? (
            <img src={project.thumbnail} alt={project.title} className="w-full h-full object-cover" />
          ) : (
            <svg className="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          )}
        </div>
        <span className={`absolute top-2 right-2 px-2 py-1 text-xs font-medium rounded-full ${status.color}`}>
          {status.label}
        </span>
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">{project.title}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {styleLabels[project.style] || project.style} · {new Date(project.created_at).toLocaleDateString('zh-CN')}
            </p>
          </div>
          <div className="relative ml-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(!showMenu);
              }}
              className="p-1 rounded-full hover:bg-gray-100 text-gray-500 transition-colors"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z" />
              </svg>
            </button>
            {showMenu && (
              <div className="absolute right-0 mt-1 w-32 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onEdit(project);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  编辑
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onDelete(project.id);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  删除
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const CreateProjectModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  editProject?: Project | null;
}> = ({ isOpen, onClose, onSuccess, editProject }) => {
  const [title, setTitle] = useState('');
  const [style, setStyle] = useState<string>('anime');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (editProject) {
      setTitle(editProject.title);
      setStyle(editProject.style || 'anime');
    } else {
      setTitle('');
      setStyle('anime');
    }
    setError('');
  }, [editProject, isOpen]);

  const styles = [
    { value: 'anime', label: '动漫', description: '日式动漫风格' },
    { value: 'realistic', label: '写实', description: '逼真的人物刻画' },
    { value: 'cyberpunk', label: '赛博朋克', description: '未来科技感' },
    { value: 'ink', label: '水墨', description: '中国传统水墨画' },
    { value: 'bw', label: '黑白', description: '经典黑白漫画' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('请输入项目标题');
      return;
    }
    if (title.length > 50) {
      setError('标题不能超过50个字符');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const userId = localStorage.getItem('user_id') || 'default_user';
      const url = editProject
        ? `${API_BASE_URL}/api/projects/${editProject.id}`
        : `${API_BASE_URL}/api/projects`;
      const method = editProject ? 'PUT' : 'POST';
      const body = editProject
        ? { title: title.trim(), settings: { style } }
        : { user_id: userId, title: title.trim(), settings: { style } };

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('操作失败');
      }

      onSuccess();
      onClose();
    } catch (err) {
      setError('操作失败,请重试');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {editProject ? '编辑项目' : '新建项目'}
          </h2>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-100 text-gray-500">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">项目标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={50}
              placeholder="请输入项目标题"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
            />
            <div className="flex justify-between mt-1">
              {error ? <p className="text-sm text-red-500">{error}</p> : <span />}
              <span className="text-sm text-gray-400">{title.length}/50</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">选择风格</label>
            <div className="grid grid-cols-1 gap-2">
              {styles.map((s) => (
                <label
                  key={s.value}
                  className={`flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    style === s.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="style"
                    value={s.value}
                    checked={style === s.value}
                    onChange={(e) => setStyle(e.target.value)}
                    className="sr-only"
                  />
                  <div className="flex-1">
                    <span className="font-medium text-gray-900">{s.label}</span>
                    <p className="text-sm text-gray-500">{s.description}</p>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      style === s.value ? 'border-blue-500' : 'border-gray-300'
                    }`}
                  >
                    {style === s.value && <div className="w-3 h-3 rounded-full bg-blue-500" />}
                  </div>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? '处理中...' : editProject ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const ProjectFilter: React.FC<{
  currentFilter: string;
  onFilterChange: (filter: string) => void;
  counts: Record<string, number>;
}> = ({ currentFilter, onFilterChange, counts }) => {
  const filters = [
    { value: 'all', label: '全部', count: counts.all || 0 },
    { value: 'generating', label: '进行中', count: counts.generating || 0 },
    { value: 'completed', label: '已完成', count: counts.completed || 0 },
    { value: 'draft', label: '草稿', count: counts.draft || 0 },
  ];

  return (
    <div className="flex gap-2 flex-wrap">
      {filters.map((filter) => (
        <button
          key={filter.value}
          onClick={() => onFilterChange(filter.value)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            currentFilter === filter.value
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {filter.label}
          <span className={`ml-1.5 ${currentFilter === filter.value ? 'text-blue-200' : 'text-gray-400'}`}>
            {filter.count}
          </span>
        </button>
      ))}
    </div>
  );
};

const ProjectManagementPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editProject, setEditProject] = useState<Project | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects`);
      if (response.ok) {
        const data = await response.json();
        setProjects(Array.isArray(data) ? data : data.projects || []);
      } else {
        setProjects([]);
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (id: string) => {
    setDeleteConfirm(id);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/${deleteConfirm}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setProjects(projects.filter((p) => p.id !== deleteConfirm));
      }
    } catch (error) {
      console.error('Delete failed:', error);
    }
    setDeleteConfirm(null);
  };

  const handleEdit = (project: Project) => {
    setEditProject(project);
    setIsModalOpen(true);
  };

  const handleProjectClick = (project: Project) => {
    window.location.href = `/project/${project.id}`;
  };

  const counts = {
    all: projects.length,
    draft: projects.filter((p) => p.status === 'draft').length,
    generating: projects.filter((p) => p.status === 'generating').length,
    completed: projects.filter((p) => p.status === 'completed').length,
  };

  const filteredProjects = filter === 'all'
    ? projects
    : projects.filter((p) => p.status === filter);

  return (
    <AppLayout>
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">项目管理</h1>
              <p className="text-gray-500 mt-1">管理和查看您的所有创作项目</p>
            </div>
            <button
              onClick={() => {
                setEditProject(null);
                setIsModalOpen(true);
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors shadow-sm"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              新建项目
            </button>
          </div>

          <div className="mb-6">
            <ProjectFilter currentFilter={filter} onFilterChange={setFilter} counts={counts} />
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-xl shadow-sm overflow-hidden animate-pulse">
                  <div className="aspect-video bg-gray-200" />
                  <div className="p-4 space-y-3">
                    <div className="h-5 bg-gray-200 rounded w-3/4" />
                    <div className="h-4 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm p-12 text-center">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-1">暂无项目</h3>
              <p className="text-gray-500 mb-6">创建您的第一个 AI 漫画项目</p>
              <button
                onClick={() => {
                  setEditProject(null);
                  setIsModalOpen(true);
                }}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                新建项目
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onClick={handleProjectClick}
                />
              ))}
            </div>
          )}
        </div>

        <CreateProjectModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setEditProject(null);
          }}
          onSuccess={fetchProjects}
          editProject={editProject}
        />

        {deleteConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/50" onClick={() => setDeleteConfirm(null)} />
            <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">确认删除</h3>
              <p className="text-gray-500 mb-6">确定要删除这个项目吗?此操作无法撤销。</p>
              <div className="flex gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={confirmDelete}
                  className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default ProjectManagementPage;