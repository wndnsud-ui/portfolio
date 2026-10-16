import { useState } from 'react';
import { speakerName, type Speaker } from '../../types/speaker';
import { josa } from '../../utils/josa';
import { Dialog } from '../common/Dialog';
import { SpeakerAvatar } from '../transcript/SpeakerBadge';

interface Props {
  from: Speaker;
  speakers: Speaker[];
  onClose: () => void;
  onConfirm: (intoId: string) => Promise<void>;
}

export function SpeakerMergeDialog({ from, speakers, onClose, onConfirm }: Props) {
  const targets = speakers.filter((s) => s.id !== from.id);
  const [target, setTarget] = useState(targets[0]?.id ?? '');
  const [busy, setBusy] = useState(false);
  const picked = targets.find((t) => t.id === target);
  const fromName = speakerName(from);

  return (
    <Dialog
      title={`${josa(fromName, '을/를')} 누구와 합칠까요?`}
      description={`${fromName}의 문장 ${from.segment_count}개가 선택한 화자로 바뀌어요.`}
      onClose={onClose}
      actions={
        <>
          <button type="button" className="btn" onClick={onClose}>
            취소
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!picked || busy}
            onClick={async () => {
              setBusy(true);
              await onConfirm(target);
              setBusy(false);
            }}
          >
            {picked ? `${speakerName(picked)}에 병합` : '병합'}
          </button>
        </>
      }
    >
      <div
        role="radiogroup"
        aria-label="합칠 화자"
        style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        onKeyDown={(e) => {
          if (!['ArrowDown', 'ArrowUp'].includes(e.key)) return;
          e.preventDefault();
          const i = targets.findIndex((t) => t.id === target);
          const next = targets[(i + (e.key === 'ArrowDown' ? 1 : targets.length - 1)) % targets.length];
          if (next) setTarget(next.id);
        }}
      >
        {targets.map((t) => (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={t.id === target}
            className="radio-row"
            onClick={() => setTarget(t.id)}
          >
            <span className="radio-ring" aria-hidden="true" />
            <SpeakerAvatar speaker={t} size={28} />
            <span style={{ flex: 1, fontWeight: 500 }}>{speakerName(t)}</span>
            <span className="xsmall muted">문장 {t.segment_count}개</span>
          </button>
        ))}
      </div>
    </Dialog>
  );
}
