// /root/.openclaw/projects/AiComic/outputs/spec_impl_SPEC-AiComic-1774874943-03.py
import React, { useState, useEffect, useCallback } from 'react';
import { 
  DndContext, 
  closestCenter, 
  KeyboardSensor, 
  PointerSensor, 
  useSensor, 
  useSensors, 
  DragEndEvent 
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import axios from 'axios';

const API_BASE_URL = 'http://47.121.27.3:8000';

interface Shot {
  id: string;
  type: string;
  duration: number;
  keywords: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  description: string;
  thumbnailUrl?: string;
}

interface Scene {
  id: string;
  location: string;
  shots: Shot[];
}

interface Storyboard {
  project_id: string;
  storyboard: Scene[];
}

interface SortableShotCardProps {
  shot: Shot;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onClick: (shot: Shot) => void;
}

function SortableShotCard({ shot, isSelected, onSelect, onClick }: SortableShotCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: shot.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-400';
      case 'generating':
        return 'bg-yellow-500 animate-pulse';
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-400';
    }
  };

  const getTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'wide':
        return 'bg-purple-100 text-purple-700';
      case 'medium':
        return 'bg-blue-100 text-blue-700';
      case 'close-up':
        return 'bg-orange-100 text-orange-700';
      case 'detail':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        relative rounded-lg overflow-hidden cursor-pointer transition-all duration-200
        ${isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'}
        ${isDragging ? 'z-50 shadow-2xl' : ''}
        bg-white border border-gray-200
      `}
      onClick={() => onClick(shot)}
    >
      <div className="relative aspect-video bg-gray-100">
        {shot.status === 'completed' && shot.thumbnailUrl ? (
          <img
            src={shot.thumbnailUrl}
            alt={shot.description}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-200 to-gray-300">
            {shot.status === 'generating' ? (
              <svg className="w-8 h-8 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            )}
          </div>
        )}
        <div className={`absolute top-2 right-2 w-3 h-3 rounded-full ${getStatusColor(shot.status)}`} />
      </div>

      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${getTypeBadgeColor(shot.type)}`}>
            {shot.type.replace('-', ' ')}
          </span>
          <span className="text-xs text-gray-500">{shot.duration}s</span>
        </div>
        <p className="text-sm text-gray-700 line-clamp-2 mb-2">{shot.description}</p>
        <p className="text-xs text-gray-400 truncate">{shot.keywords}</p>
      </div>

      <div
        className={`
          absolute top-2 left-2 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
          ${isSelected ? 'bg-blue-500 border-blue-500' : 'bg-white border-gray-300 hover:border-blue-400'}
        `}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(shot.id);
        }}
      >
        {isSelected && (
          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )}
      </div>
    </div>
  );
}

interface SceneNavProps {
  scenes: Scene[];
  currentSceneIndex: number;
  onSceneSelect: (index: number) => void;
  onAddScene: () => void;
}

function SceneNav({ scenes, currentSceneIndex, onSceneSelect, onAddScene }: SceneNavProps) {
  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">场景列表</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {scenes.map((scene, index) => (
          <button
            key={scene.id}
            onClick={() => onSceneSelect(index)}
            className={`
              w-full text-left px-3 py-2 rounded-lg mb-1 transition-colors
              ${currentSceneIndex === index 
                ? 'bg-blue-50 text-blue-700 font-medium' 
                : 'text-gray-600 hover:bg-gray-50'}
            `}
          >
            <div className="flex items-center justify-between">
              <span className="truncate flex-1">{scene.location}</span>
              <span className="ml-2 text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                {scene.shots.length}
              </span>
            </div>
          </button>
        ))}
      </div>
      <div className="p-3 border-t border-gray-200">
        <button
          onClick={onAddScene}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          新增场景
        </button>
      </div>
    </div>
  );
}

interface ShotCardProps {
  shot: Shot;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onClick: (shot: Shot) => void;
}

function ShotCard({ shot, isSelected, onSelect, onClick }: ShotCardProps) {
  return (
    <SortableShotCard 
      shot={shot} 
      isSelected={isSelected} 
      onSelect={onSelect} 
      onClick={onClick}
    />
  );
}

interface BatchActionBarProps {
  selectedCount: number;
  onBatchGenerate: () => void;
  onClearSelection: () => void;
  isGenerating: boolean;
}

function BatchActionBar({ selectedCount, onBatchGenerate, onClearSelection, isGenerating }: BatchActionBarProps) {
  return (
    <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-white rounded-xl shadow-2xl border border-gray-200 px-6 py-4 flex items-center gap-4">
      <span className="text-sm text-gray-600">
        已选中 <span className="font-semibold text-gray-900">{selectedCount}</span> 个镜头
      </span>
      <div className="flex items-center gap-2">
        {selectedCount > 0 && (
          <button
            onClick={onClearSelection}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            取消选择
          </button>
        )}
        <button
          onClick={onBatchGenerate}
          disabled={selectedCount === 0 || isGenerating}
          className={`
            px-6 py-2 rounded-lg text-white font-medium transition-all
            ${selectedCount === 0 || isGenerating
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg hover:shadow-xl'}
          `}
        >
          {isGenerating ? (
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              生成中...
            </span>
          ) : (
            '批量生成'
          )}
        </button>
      </div>
    </div>
  );
}

interface ShotDetailDrawerProps {
  shot: Shot | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (shot: Shot) => void;
}

function ShotDetailDrawer({ shot, isOpen, onClose, onSave }: ShotDetailDrawerProps) {
  const [localShot, setLocalShot] = useState<Shot | null>(shot);

  useEffect(() => {
    setLocalShot(shot);
  }, [shot]);

  if (!isOpen || !localShot) return null;

  const shotTypes = ['wide', 'medium', 'close-up', 'detail'];

  const handleSave = () => {
    if (localShot) {
      onSave(localShot);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black bg-opacity-30" onClick={onClose} />
      <div className="absolute right-0 top-0 bottom-0 w-full max-w-md bg-white shadow-2xl transform transition-transform">
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">镜头详情</h3>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">镜头类型</label>
              <div className="grid grid-cols-2 gap-2">
                {shotTypes.map((type) => (
                  <button
                    key={type}
                    onClick={() => setLocalShot({ ...localShot, type })}
                    className={`
                      px-4 py-2 text-sm rounded-lg border-2 transition-all
                      ${localShot.type === type
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'}
                    `}
                  >
                    {type.replace('-', ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                时长 (秒)
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="30"
                value={localShot.duration}
                onChange={(e) => setLocalShot({ ...localShot, duration: parseFloat(e.target.value) || 0 })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                镜头描述
              </label>
              <textarea
                value={localShot.description}
                onChange={(e) => setLocalShot({ ...localShot, description: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                placeholder="描述这个镜头的内容..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                关键词
              </label>
              <input
                type="text"
                value={localShot.keywords}
                onChange={(e) => setLocalShot({ ...localShot, keywords: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="classroom, desk, window..."
              />
              <p className="mt-1 text-xs text-gray-400">用逗号分隔多个关键词</p>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-3">动态效果配置</h4>
              <button className="w-full px-4 py-3 bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                </svg>
                打开动效编辑器
              </button>
            </div>
          </div>

          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StoryboardManagementPage() {
  const [projectId] = useState<string>('demo-project-id');
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [selectedShots, setSelectedShots] = useState<Set<string>>(new Set());
  const [selectedShot, setSelectedShot] = useState<Shot | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const fetchStoryboard = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await axios.get<Storyboard>(
        `${API_BASE_URL}/api/projects/${projectId}/storyboard`
      );
      setStoryboard(response.data);
    } catch (error) {
      console.error('Failed to fetch storyboard:', error);
      setStoryboard({
        project_id: projectId,
        storyboard: [
          {
            id: 'scene-1',
            location: '场景1:教室',
            shots: [
              {
                id: 'shot-1',
                type: 'medium',
                duration: 5.0,
                keywords: 'classroom, desk',
                status: 'pending',
                description: '小明走进教室',
              },
              {
                id: 'shot-2',
                type: 'wide',
                duration: 8.0,
                keywords: 'classroom全景',
                status: 'completed',
                description: '教室全景展示',
                thumbnailUrl: '',
              },
              {
                id: 'shot-3',
                type: 'close-up',
                duration: 3.0,
                keywords: '黑板, 粉笔',
                status: 'generating',
                description: '黑板特写',
              },
            ],
          },
          {
            id: 'scene-2',
            location: '场景2:操场',
            shots: [
              {
                id: 'shot-4',
                type: 'wide',
                duration: 10.0,
                keywords: '操场, 跑道',
                status: 'pending',
                description: '操场远景',
              },
            ],
          },
        ],
      });
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchStoryboard();
  }, [fetchStoryboard]);

  const currentScene = storyboard?.storyboard[currentSceneIndex];

  const handleShotSelect = (shotId: string) => {
    const newSelected = new Set(selectedShots);
    if (newSelected.has(shotId)) {
      newSelected.delete(shotId);
    } else {
      newSelected.add(shotId);
    }
    setSelectedShots(newSelected);
  };

  const handleShotClick = (shot: Shot) => {
    setSelectedShot(shot);
    setIsDrawerOpen(true);
  };

  const handleClearSelection = () => {
    setSelectedShots(new Set());
  };

  const handleBatchGenerate = async () => {
    if (selectedShots.size === 0) return;

    setIsGenerating(true);
    try {
      await axios.post(
        `${API_BASE_URL}/api/projects/${projectId}/shots/generate-batch`,
        {
          shot_ids: Array.from(selectedShots),
        }
      );

      const updatedStoryboard = { ...storyboard! };
      updatedStoryboard.storyboard = updatedStoryboard.storyboard.map((scene) => ({
        ...scene,
        shots: scene.shots.map((shot) =>
          selectedShots.has(shot.id) ? { ...shot, status: 'generating' as const } : shot
        ),
      }));
      setStoryboard(updatedStoryboard);
      setSelectedShots(new Set());
    } catch (error) {
      console.error('Failed to generate shots:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAddScene = () => {
    if (!storyboard) return;
    const newScene: Scene = {
      id: `scene-${Date.now()}`,
      location: `场景${storyboard.storyboard.length + 1}:新场景`,
      shots: [],
    };
    setStoryboard({
      ...storyboard,
      storyboard: [...storyboard.storyboard, newScene],
    });
    setCurrentSceneIndex(storyboard.storyboard.length);
  };

  const handleSaveShot = (updatedShot: Shot) => {
    if (!storyboard || !currentScene) return;
    const updatedStoryboard = { ...storyboard };
    const sceneIndex = updatedStoryboard.storyboard.findIndex((s) => s.id === currentScene.id);
    if (sceneIndex !== -1) {
      updatedStoryboard.storyboard[sceneIndex].shots = updatedStoryboard.storyboard[
        sceneIndex
      ].shots.map((s) => (s.id === updatedShot.id ? updatedShot : s));
      setStoryboard(updatedStoryboard);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !currentScene) return;

    const oldIndex = currentScene.shots.findIndex((s) => s.id === active.id);
    const newIndex = currentScene.shots.findIndex((s) => s.id === over.id);

    const newShots = arrayMove(currentScene.shots, oldIndex, newIndex);
    const updatedStoryboard = { ...storyboard! };
    updatedStoryboard.storyboard = updatedStoryboard.storyboard.map((scene, index) =>
      index === currentSceneIndex ? { ...scene, shots: newShots } : scene
    );
    setStoryboard(updatedStoryboard);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <svg className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">分镜管理</h1>
              <p className="text-sm text-gray-500 mt-1">
                {currentScene?.location || '选择场景'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors">
                预览
              </button>
              <button className="px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors">
                导出
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-73px)]">
        <SceneNav
          scenes={storyboard?.storyboard || []}
          currentSceneIndex={currentSceneIndex}
          onSceneSelect={setCurrentSceneIndex}
          onAddScene={handleAddScene}
        />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-800">
                {currentScene?.location || '暂无场景'}
              </h2>
              <span className="text-sm text-gray-500">
                {currentScene?.shots.length || 0} 个镜头
              </span>
            </div>

            {currentScene && currentScene.shots.length > 0 ? (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={currentScene.shots.map((s) => s.id)}
                  strategy={verticalListSortingStrategy}
                >
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {currentScene.shots.map((shot) => (
                      <ShotCard
                        key={shot.id}
                        shot={shot}
                        isSelected={selectedShots.has(shot.id)}
                        onSelect={handleShotSelect}
                        onClick={handleShotClick}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            ) : (
              <div className="text-center py-16">
                <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
                </svg>
                <h3 className="text-lg font-medium text-gray-600 mb-2">暂无镜头</h3>
                <p className="text-sm text-gray-400">添加场景后可开始创建镜头</p>
              </div>
            )}
          </div>
        </main>
      </div>

      <BatchActionBar
        selectedCount={selectedShots.size}
        onBatchGenerate={handleBatchGenerate}
        onClearSelection={handleClearSelection}
        isGenerating={isGenerating}
      />

      <ShotDetailDrawer
        shot={selectedShot}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedShot(null);
        }}
        onSave={handleSaveShot}
      />
    </div>
  );
}