import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { ChevronLeft, Play, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

const API_BASE_URL = 'http://47.121.27.3:8000';

interface MotionType {
  value: string;
  label: string;
  type: string;
}

interface Shot {
  id: string;
  title: string;
  thumbnail?: string;
}

interface MotionConfig {
  motion_type: string;
  speed: string;
  micro_animations: string[];
  transition: string;
}

const motionSpeedDuration: Record<string, string> = {
  slow: '2s',
  medium: '1s',
  fast: '0.5s',
};

const motionAnimations: Record<string, { keyframes: string; name: string }> = {
  pan_left: {
    name: 'panLeft',
    keyframes: '@keyframes panLeft { 0% { transform: translateX(20%); } 100% { transform: translateX(0); } }',
  },
  pan_right: {
    name: 'panRight',
    keyframes: '@keyframes panRight { 0% { transform: translateX(-20%); } 100% { transform: translateX(0); } }',
  },
  zoom_in: {
    name: 'zoomIn',
    keyframes: '@keyframes zoomIn { 0% { transform: scale(0.8); } 100% { transform: scale(1); } }',
  },
  zoom_out: {
    name: 'zoomOut',
    keyframes: '@keyframes zoomOut { 0% { transform: scale(1.2); } 100% { transform: scale(1); } }',
  },
  tilt_up: {
    name: 'tiltUp',
    keyframes: '@keyframes tiltUp { 0% { transform: translateY(15%) rotateX(-10deg); } 100% { transform: translateY(0) rotateX(0); } }',
  },
  tilt_down: {
    name: 'tiltDown',
    keyframes: '@keyframes tiltDown { 0% { transform: translateY(-15%) rotateX(10deg); } 100% { transform: translateY(0) rotateX(0); } }',
  },
  rotate: {
    name: 'rotate',
    keyframes: '@keyframes rotate { 0% { transform: rotate(-5deg); } 50% { transform: rotate(5deg); } 100% { transform: rotate(-5deg); } }',
  },
  shake: {
    name: 'shake',
    keyframes: '@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px) rotate(-1deg); } 75% { transform: translateX(5px) rotate(1deg); } }',
  },
  push_in: {
    name: 'pushIn',
    keyframes: '@keyframes pushIn { 0% { transform: scale(0.9) translateZ(-50px); opacity: 0.5; } 100% { transform: scale(1) translateZ(0); opacity: 1; } }',
  },
  fixed: {
    name: 'static',
    keyframes: '@keyframes static { 0%, 100% { transform: translateX(0) translateY(0) scale(1); } }',
  },
};

const microAnimationStyles: Record<string, React.CSSProperties> = {
  hair_float: { animation: 'hairFloat 3s ease-in-out infinite' },
  breathing: { animation: 'breathing 4s ease-in-out infinite' },
  eye_blink: { animation: 'eyeBlink 4s ease-in-out infinite' },
  cloth_sway: { animation: 'clothSway 2.5s ease-in-out infinite' },
  head_turn: { animation: 'headTurn 5s ease-in-out infinite' },
};

export default function MotionConfigPage() {
  const router = useRouter();
  const { projectId } = router.query;
  
  const [shots, setShots] = useState<Shot[]>([]);
  const [selectedShotId, setSelectedShotId] = useState<string>('');
  const [motionTypes, setMotionTypes] = useState<MotionType[]>([]);
  const [motionTypeGroups, setMotionTypeGroups] = useState<Record<string, MotionType[]>>({});
  
  const [motionType, setMotionType] = useState<string>('fixed');
  const [speed, setSpeed] = useState<string>('medium');
  const [microAnimations, setMicroAnimations] = useState<string[]>([]);
  const [transition, setTransition] = useState<string>('none');
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);

  useEffect(() => {
    if (projectId) {
      fetchMotionTypes();
      fetchShots();
    }
  }, [projectId]);

  useEffect(() => {
    const grouped = motionTypes.reduce((acc, item) => {
      const type = item.type || 'other';
      if (!acc[type]) acc[type] = [];
      acc[type].push(item);
      return acc;
    }, {} as Record<string, MotionType[]>);
    setMotionTypeGroups(grouped);
  }, [motionTypes]);

  const fetchMotionTypes = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/options/motion-types`);
      if (response.ok) {
        const data = await response.json();
        setMotionTypes(data);
      }
    } catch (error) {
      console.error('Failed to fetch motion types:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchShots = async () => {
    try {
      const mockShots: Shot[] = [
        { id: 'shot-1', title: '分镜1 - 开场' },
        { id: 'shot-2', title: '分镜2 - 人物介绍' },
        { id: 'shot-3', title: '分镜3 - 场景切换' },
        { id: 'shot-4', title: '分镜4 - 高潮' },
        { id: 'shot-5', title: '分镜5 - 结尾' },
      ];
      setShots(mockShots);
      if (mockShots.length > 0) {
        setSelectedShotId(mockShots[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch shots:', error);
    }
  };

  const handleMicroAnimationToggle = (value: string) => {
    setMicroAnimations(prev => 
      prev.includes(value) 
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  const handleApplyMotion = async () => {
    if (!projectId || !selectedShotId) return;
    
    try {
      setSaving(true);
      const payload: MotionConfig = {
        motion_type: motionType,
        speed,
        micro_animations: microAnimations,
        transition,
      };
      
      const response = await fetch(
        `${API_BASE_URL}/api/projects/${projectId}/shots/${selectedShotId}/apply-motion`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      );
      
      if (response.ok) {
        alert('动态效果已应用');
      } else {
        alert('应用失败,请重试');
      }
    } catch (error) {
      console.error('Failed to apply motion:', error);
      alert('应用失败,请重试');
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = () => {
    setPreviewPlaying(true);
    setPreviewKey(prev => prev + 1);
    setTimeout(() => setPreviewPlaying(false), 3000);
  };

  const handleReset = () => {
    setMotionType('fixed');
    setSpeed('medium');
    setMicroAnimations([]);
    setTransition('none');
    setPreviewKey(prev => prev + 1);
  };

  const getMotionAnimation = () => {
    const duration = motionSpeedDuration[speed] || '1s';
    const motion = motionAnimations[motionType];
    
    if (!motion) return { animation: 'none', duration };
    
    return {
      animation: `${motion.name} ${duration} ease-out`,
      duration,
    };
  };

  const getTransitionStyle = () => {
    const transitions: Record<string, React.CSSProperties> = {
      none: {},
      black: { backgroundColor: '#000' },
      white: { backgroundColor: '#fff' },
      crossfade: { animation: 'crossfade 1s ease-in-out' },
      slide: { animation: 'slide 1s ease-in-out' },
      fade: { animation: 'fade 1s ease-in-out' },
    };
    return transitions[transition] || {};
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <style jsx global>{`
        @keyframes hairFloat {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-3px) rotate(2deg); }
        }
        @keyframes breathing {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.02); }
        }
        @keyframes eyeBlink {
          0%, 45%, 55%, 100% { transform: scaleY(1); }
          50% { transform: scaleY(0.1); }
        }
        @keyframes clothSway {
          0%, 100% { transform: skewX(0deg); }
          25% { transform: skewX(2deg); }
          75% { transform: skewX(-2deg); }
        }
        @keyframes headTurn {
          0%, 100% { transform: rotateY(0deg); }
          50% { transform: rotateY(10deg); }
        }
        @keyframes crossfade {
          0% { opacity: 0; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
        @keyframes slide {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(0); }
        }
        @keyframes fade {
          0% { opacity: 0; }
          100% { opacity: 1; }
        }
        ${Object.values(motionAnimations).map(m => m.keyframes).join('\n')}
      `}</style>

      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-lg border-b border-slate-700">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="text-slate-300 hover:text-white hover:bg-slate-700"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              返回
            </Button>
            <h1 className="text-xl font-bold text-white">动态效果配置</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="border-slate-600 text-slate-300 hover:bg-slate-700"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              重置
            </Button>
            <Button
              size="sm"
              onClick={handleApplyMotion}
              disabled={saving || !selectedShotId}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {saving ? '应用中...' : '应用配置'}
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  选择分镜
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ShotSelector
                  shots={shots}
                  selectedShotId={selectedShotId}
                  onSelect={setSelectedShotId}
                />
              </CardContent>
            </Card>

            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                  动态效果配置
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <MotionTypeSection
                  motionTypeGroups={motionTypeGroups}
                  selectedMotionType={motionType}
                  onSelect={setMotionType}
                  loading={loading}
                />

                <Separator className="bg-slate-700" />

                <MotionSpeedSection
                  selectedSpeed={speed}
                  onSelect={setSpeed}
                />

                <Separator className="bg-slate-700" />

                <MicroAnimationSection
                  selectedAnimations={microAnimations}
                  onToggle={handleMicroAnimationToggle}
                />

                <Separator className="bg-slate-700" />

                <TransitionSection
                  selectedTransition={transition}
                  onSelect={setTransition}
                />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="bg-slate-800/50 border-slate-700 sticky top-24">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg text-white">效果预览</CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePreview}
                    className="border-slate-600 text-slate-300 hover:bg-slate-700"
                  >
                    <Play className="w-4 h-4 mr-1" />
                    播放
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <PreviewPanel
                  motionType={motionType}
                  speed={speed}
                  microAnimations={microAnimations}
                  transition={transition}
                  previewKey={previewKey}
                  previewPlaying={previewPlaying}
                  getMotionAnimation={getMotionAnimation}
                  getTransitionStyle={getTransitionStyle}
                  microAnimationStyles={microAnimationStyles}
                />
              </CardContent>
            </Card>

            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg text-white">当前配置</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <ConfigItem label="运动类型" value={motionType} />
                  <ConfigItem label="运动速度" value={speed} />
                  <ConfigItem 
                    label="微动效" 
                    value={microAnimations.length > 0 ? microAnimations.join(', ') : '无'} 
                  />
                  <ConfigItem label="转场效果" value={transition} />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ShotSelectorProps {
  shots: Shot[];
  selectedShotId: string;
  onSelect: (id: string) => void;
}

function ShotSelector({ shots, selectedShotId, onSelect }: ShotSelectorProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
      {shots.map((shot) => (
        <button
          key={shot.id}
          onClick={() => onSelect(shot.id)}
          className={`relative group p-3 rounded-lg border-2 transition-all ${
            selectedShotId === shot.id
              ? 'border-blue-500 bg-blue-500/20'
              : 'border-slate-600 bg-slate-700/50 hover:border-slate-500 hover:bg-slate-700'
          }`}
        >
          <div className="aspect-video bg-slate-600 rounded mb-2 overflow-hidden">
            <div className="w-full h-full bg-gradient-to-br from-slate-500 to-slate-600 flex items-center justify-center">
              <span className="text-xs text-slate-300">预览</span>
            </div>
          </div>
          <p className="text-xs text-slate-300 truncate text-center">
            {shot.title}
          </p>
          {selectedShotId === shot.id && (
            <div className="absolute top-2 right-2">
              <Badge className="bg-blue-500 text-white text-xs">选中</Badge>
            </div>
          )}
        </button>
      ))}
    </div>
  );
}

interface MotionTypeSectionProps {
  motionTypeGroups: Record<string, MotionType[]>;
  selectedMotionType: string;
  onSelect: (value: string) => void;
  loading: boolean;
}

function MotionTypeSection({ motionTypeGroups, selectedMotionType, onSelect, loading }: MotionTypeSectionProps) {
  const groupLabels: Record<string, string> = {
    none: '静止',
    translate: '平移',
    scale: '缩放',
    rotate: '旋转',
    shake: '震动',
    other: '其他',
  };

  const groupOrder = ['none', 'translate', 'scale', 'rotate', 'shake', 'other'];

  if (loading) {
    return (
      <div className="space-y-3">
        <Label className="text-slate-300 font-medium">运动类型</Label>
        <div className="h-10 bg-slate-700 rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <Label className="text-slate-300 font-medium">运动类型</Label>
      <Tabs defaultValue="none" className="w-full">
        <TabsList className="bg-slate-700 border-slate-600">
          {groupOrder.map((groupKey) => (
            motionTypeGroups[groupKey] && (
              <TabsTrigger
                key={groupKey}
                value={groupKey}
                className="data-[state=active]:bg-slate-600 text-slate-300"
              >
                {groupLabels[groupKey] || groupKey}
              </TabsTrigger>
            )
          ))}
        </TabsList>
        {groupOrder.map((groupKey) => (
          motionTypeGroups[groupKey] && (
            <TabsContent key={groupKey} value={groupKey} className="mt-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {motionTypeGroups[groupKey].map((item) => (
                  <button
                    key={item.value}
                    onClick={() => onSelect(item.value)}
                    className={`p-3 rounded-lg border text-sm transition-all ${
                      selectedMotionType === item.value
                        ? 'border-blue-500 bg-blue-500/20 text-white'
                        : 'border-slate-600 bg-slate-700/50 text-slate-300 hover:border-slate-500'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </TabsContent>
          )
        ))}
      </Tabs>
    </div>
  );
}

interface MotionSpeedSectionProps {
  selectedSpeed: string;
  onSelect: (value: string) => void;
}

function MotionSpeedSection({ selectedSpeed, onSelect }: MotionSpeedSectionProps) {
  const speeds = [
    { value: 'slow', label: '慢速', description: '2秒' },
    { value: 'medium', label: '中速', description: '1秒' },
    { value: 'fast', label: '快速', description: '0.5秒' },
  ];

  return (
    <div className="space-y-3">
      <Label className="text-slate-300 font-medium">运动速度</Label>
      <RadioGroup
        value={selectedSpeed}
        onValueChange={onSelect}
        className="flex gap-4"
      >
        {speeds.map((speed) => (
          <div key={speed.value} className="flex items-center space-x-2">
            <RadioGroupItem
              value={speed.value}
              id={speed.value}
              className="border-slate-500 text-blue-500"
            />
            <Label
              htmlFor={speed.value}
              className="text-slate-300 cursor-pointer flex items-center gap-2"
            >
              {speed.label}
              <span className="text-xs text-slate-500">({speed.description})</span>
            </Label>
          </div>
        ))}
      </RadioGroup>
    </div>
  );
}

interface MicroAnimationSectionProps {
  selectedAnimations: string[];
  onToggle: (value: string) => void;
}

function MicroAnimationSection({ selectedAnimations, onToggle }: MicroAnimationSectionProps) {
  const animations = [
    { value: 'hair_float', label: '发丝飘动' },
    { value: 'breathing', label: '呼吸效果' },
    { value: 'eye_blink', label: '眨眼动画' },
    { value: 'cloth_sway', label: '衣物摆动' },
    { value: 'head_turn', label: '轻微转头' },
  ];

  return (
    <div className="space-y-3">
      <Label className="text-slate-300 font-medium">微动效 (可多选)</Label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {animations.map((anim) => (
          <div key={anim.value} className="flex items-center space-x-2">
            <Checkbox
              id={anim.value}
              checked={selectedAnimations.includes(anim.value)}
              onCheckedChange={() => onToggle(anim.value)}
              className="border-slate-500 data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500"
            />
            <Label
              htmlFor={anim.value}
              className="text-slate-300 cursor-pointer text-sm"
            >
              {anim.label}
            </Label>
          </div>
        ))}
      </div>
      {selectedAnimations.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selectedAnimations.map((anim) => (
            <Badge
              key={anim}
              variant="secondary"
              className="bg-blue-500/20 text-blue-300 border border-blue-500/30"
            >
              {animations.find(a => a.value === anim)?.label}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

interface TransitionSectionProps {
  selectedTransition: string;
  onSelect: (value: string) => void;
}

function TransitionSection({ selectedTransition, onSelect }: TransitionSectionProps) {
  const transitions = [
    { value: 'none', label: '无' },
    { value: 'black', label: '黑场' },
    { value: 'white', label: '白场' },
    { value: 'crossfade', label: '交叉淡入淡出' },
    { value: 'slide', label: '滑入' },
    { value: 'fade', label: '淡入淡出' },
  ];

  return (
    <div className="space-y-3">
      <Label className="text-slate-300 font-medium">转场效果</Label>
      <Select value={selectedTransition} onValueChange={onSelect}>
        <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-200">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-slate-700 border-slate-600">
          {transitions.map((t) => (
            <SelectItem key={t.value} value={t.value} className="text-slate-200">
              {t.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface PreviewPanelProps {
  motionType: string;
  speed: string;
  microAnimations: string[];
  transition: string;
  previewKey: number;
  previewPlaying: boolean;
  getMotionAnimation: () => { animation: string; duration: string };
  getTransitionStyle: () => React.CSSProperties;
  microAnimationStyles: Record<string, React.CSSProperties>;
}

function PreviewPanel({
  motionType,
  speed,
  microAnimations,
  transition,
  previewKey,
  previewPlaying,
  getMotionAnimation,
  getTransitionStyle,
  microAnimationStyles,
}: PreviewPanelProps) {
  const motionStyle = getMotionAnimation();
  const transitionStyle = getTransitionStyle();
  
  const combinedMicroStyles = microAnimations.reduce((acc, anim) => {
    if (microAnimationStyles[anim]) {
      return { ...acc, ...microAnimationStyles[anim] };
    }
    return acc;
  }, {} as React.CSSProperties);

  return (
    <div key={previewKey} className="space-y-4">
      <div
        className="relative aspect-video bg-gradient-to-br from-slate-700 to-slate-800 rounded-lg overflow-hidden border border-slate-600"
        style={transitionStyle}
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className="w-32 h-32 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg shadow-2xl"
            style={{
              ...motionStyle,
              ...combinedMicroStyles,
              animationPlayState: previewPlaying ? 'running' : 'paused',
            }}
          >
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-16 h-16 bg-white/30 rounded-full" 
                   style={{
                     animation: microAnimations.includes('eye_blink') 
                       ? 'eyeBlink 4s ease-in-out infinite' 
                       : 'none',
                     animationPlayState: previewPlaying ? 'running' : 'paused',
                   }}
              />
            </div>
          </div>
        </div>
        
        <div className="absolute bottom-2 left-2 right-2 flex justify-between text-xs text-slate-400">
          <span>类型: {motionType}</span>
          <span>速度: {speed}</span>
        </div>
        
        {transition !== 'none' && (
          <div className="absolute top-2 right-2">
            <Badge variant="outline" className="border-slate-500 text-slate-300 bg-slate-800/80">
              {transition}
            </Badge>
          </div>
        )}
      </div>

      <div className="bg-slate-700/50 rounded-lg p-3">
        <p className="text-xs text-slate-400 mb-2">动画效果说明:</p>
        <p className="text-sm text-slate-300">
          {getMotionDescription(motionType, speed, microAnimations)}
        </p>
      </div>
    </div>
  );
}

function getMotionDescription(motionType: string, speed: string, microAnimations: string[]): string {
  const motionDescriptions: Record<string, string> = {
    fixed: '静态画面,无运动效果',
    pan_left: '镜头向左平推,展示更多画面内容',
    pan_right: '镜头向右平推,展示更多画面内容',
    zoom_in: '镜头向前推进,增强画面冲击力',
    zoom_out: '镜头向后拉远,展现全貌',
    tilt_up: '镜头向上倾斜拍摄',
    tilt_down: '镜头向下倾斜拍摄',
    rotate: '画面轻微旋转晃动',
    shake: '画面震动效果',
    push_in: '推进效果,模拟走进场景',
  };

  const speedText = speed === 'slow' ? '缓慢' : speed === 'medium' ? '中等' : '快速';
  const motionText = motionDescriptions[motionType] || '自定义运动';
  
  const microText = microAnimations.length > 0 
    ? `,叠加${microAnimations.length}种微动效` 
    : '';

  return `${motionText},${speedText}速度${microText}`;
}

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-sm text-slate-200 font-medium capitalize">{value}</span>
    </div>
  );
}