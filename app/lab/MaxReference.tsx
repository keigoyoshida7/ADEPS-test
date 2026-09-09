'use client';
import { useT } from './i18n';
import { asset } from './assets';
export default function MaxReference({
  local,
  status,
  message,
  onCommand,
}: {
  local: boolean;
  status: Record<string, any> | null;
  message: string;
  onCommand: (command: string, channel?: number) => void;
}) {
  const t = useT();
  return (
    <>
      <div className="context-line">
        <span className="badge">
          {t(local ? 'ローカル接続モード' : 'Web版・実機制御なし')}
        </span>
        <p>{t('計算と実機の音声出力は別の経路です。')}</p>
      </div>
      <section className="panel">
        <h2>{t('Maxとの接続')}</h2>
        <p>
          {t(
            'Web版では再生・マイク・IRの計算をブラウザ内で行います。Max、Dante、音声出力機器には接続しません。',
          )}
        </p>
        <p>
          {t(
            '実機を試す場合はソース一式を取得し、ローカル接続モードで起動します。Maxのテストchと物理出力の対応は、使用する機器に合わせて確認してください。',
          )}
        </p>
        <div className="bridge-actions">
          <button disabled={!local} onClick={() => onCommand('ping')}>
            {t('Maxに接続確認')}
          </button>
          <button disabled={!local} onClick={() => onCommand('mute')}>
            {t('Maxへミュート要求')}
          </button>
          <span>{t(local && status?.max_reply ? '応答あり' : '未接続')}</span>
        </div>
        {message && <p role="status">{message}</p>}
      </section>
      <section className="panel">
        <h2>{t('12chのテスト出力')}</h2>
        <p>
          {t(
            'S番号はこのテストの論理chです。特定の機器のIDやDanteチャンネル番号を表しません。',
          )}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('テスト出力')}</th>
                <th>{t('ローカルMaxへ')}</th>
                <th>{t('物理出力')}</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 12 }, (_, i) => (
                <tr key={i}>
                  <td>S{i + 1}</td>
                  <td>
                    <button
                      disabled={!local}
                      onClick={() => onCommand('select', i + 1)}
                    >
                      ch {i + 1}
                    </button>
                  </td>
                  <td>{t('利用者が設定')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <h2>{t('ローカルで試す手順')}</h2>
        <ol>
          <li>
            {t('ADEPS-test.command を起動し、同梱のMaxパッチを開きます。')}
          </li>
          <li>{t('Max内のNodeブリッジをstartし、接続確認を行います。')}</li>
          <li>
            {t('Audio Statusで出力機器とchを確認し、音量0から手動で上げます。')}
          </li>
          <li>{t('終了時はMax側でSTOP。実音の停止は実機で確認します。')}</li>
        </ol>
        <a href={asset('/info/LOCAL_SETUP.md')} download>
          {t('ローカル接続の手順を保存')}
        </a>
      </section>
    </>
  );
}
