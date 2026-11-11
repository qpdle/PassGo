import { useEffect, useRef, useState } from 'react';
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode';

export default function Scanner() {
  const reader = useRef<Html5Qrcode | null>(null);
  const alive = useRef(true);
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState('Камера включается только по кнопке.');
  const [code, setCode] = useState('');

  useEffect(() => { alive.current = true; return () => {
    alive.current = false;
    const current = reader.current;
    if (current?.isScanning) void current.stop().then(() => current.clear()).catch(() => {});
  }; }, []);

  async function stop() {
    setBusy(true);
    try {
      if (reader.current?.isScanning) await reader.current.stop();
      reader.current?.clear();
      if (alive.current) setRunning(false);
    } catch { if (alive.current) setMessage('Не удалось остановить камеру. Закройте эту вкладку.'); }
    finally { if (alive.current) setBusy(false); }
  }

  async function start() {
    if (!window.isSecureContext || !navigator.mediaDevices) {
      setMessage('Для камеры нужен HTTPS или localhost. Можно ввести код вручную.');
      return;
    }
    setBusy(true);
    try {
      const current = reader.current ?? new Html5Qrcode('camera-reader', { formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE], verbose: false });
      reader.current = current;
      await current.start({ facingMode: 'environment' }, { fps: 10, qrbox: { width: 220, height: 220 } }, text => {
        if (alive.current) { setCode(text); setMessage('QR прочитан. Это проверка камеры, посещение не отмечено.'); }
      }, () => {});
      if (alive.current) { setRunning(true); setMessage('Наведите камеру на тестовый QR.'); }
      else { await current.stop(); current.clear(); }
    } catch { if (alive.current) setMessage('Камера недоступна или доступ запрещён. Проверьте разрешения либо введите код вручную.'); }
    finally { if (alive.current) setBusy(false); }
  }

  return <section className="panel"><h1>Проверка камеры</h1><p>Техническая проверка чтения QR. Подтверждение входа здесь не выполняется.</p>
    <div id="camera-reader" style={{ width: '100%', maxWidth: 420 }} />
    <p role="status">{message}</p>
    <div className="controls"><button onClick={() => void start()} disabled={busy || running}>Включить камеру</button><button onClick={() => void stop()} disabled={busy || !running}>Остановить</button></div>
    <label htmlFor="manual-code">Ручной ввод или прочитанный код</label><input id="manual-code" value={code} onChange={event => setCode(event.target.value)} autoComplete="off" />
    <button disabled={!code.trim()} onClick={() => setMessage('Код введён. Проверка билета на сервере будет добавлена отдельно.')}>Использовать код</button>
  </section>;
}
