import Button from 'antd/es/button';
import Col from 'antd/es/col';
import InputNumber from 'antd/es/input-number';
import Row from 'antd/es/row';
import Select from 'antd/es/select';
import Space from 'antd/es/space';
import Switch from 'antd/es/switch';
import Typography from 'antd/es/typography';

import { MA_COLORS, MA_WINDOW_MAX, MA_WINDOW_MIN } from '../../config/chart';
import type { CandleColorScheme, Language, PriceScale } from '../../store/configSlice';
import { colorSchemeOptions, languageOptions, scaleOptions } from './klineOptions';

interface KLineControlsProps {
  colorScheme: CandleColorScheme;
  language: Language;
  maColor: string;
  maVisible: boolean;
  maWindow: number;
  onColorSchemeChange: (value: CandleColorScheme) => void;
  onLanguageChange: (value: Language) => void;
  onMaColorChange: (value: string) => void;
  onMaVisibleChange: (value: boolean) => void;
  onMaWindowChange: (value: number) => void;
  onPriceScaleChange: (value: PriceScale) => void;
  priceScale: PriceScale;
}

export default function KLineControls({
  colorScheme,
  language,
  maColor,
  maVisible,
  maWindow,
  onColorSchemeChange,
  onLanguageChange,
  onMaColorChange,
  onMaVisibleChange,
  onMaWindowChange,
  onPriceScaleChange,
  priceScale,
}: KLineControlsProps) {
  return (
    <div className="control-panel">
      <Row gutter={[12, 12]}>
        <Col xs={12} md={6} xl={4}>
          <Typography.Text type="secondary">Scale</Typography.Text>
          <Select
            className="full-width"
            onChange={onPriceScaleChange}
            options={scaleOptions}
            value={priceScale}
          />
        </Col>
        <Col xs={12} md={6} xl={4}>
          <Typography.Text type="secondary">Bar Color</Typography.Text>
          <Select
            className="full-width"
            onChange={onColorSchemeChange}
            options={colorSchemeOptions}
            value={colorScheme}
          />
        </Col>
        <Col xs={12} md={6} xl={4}>
          <Typography.Text type="secondary">Language</Typography.Text>
          <Select
            className="full-width"
            onChange={onLanguageChange}
            options={languageOptions}
            value={language}
          />
        </Col>
        <Col xs={12} md={6} xl={4}>
          <Typography.Text type="secondary">MA</Typography.Text>
          <div>
            <Switch checked={maVisible} onChange={onMaVisibleChange} />
          </div>
        </Col>
        <Col xs={12} md={6} xl={4}>
          <Typography.Text type="secondary">MA Window</Typography.Text>
          <InputNumber
            className="full-width"
            disabled={!maVisible}
            max={MA_WINDOW_MAX}
            min={MA_WINDOW_MIN}
            onChange={(value) => onMaWindowChange(Number(value || 1))}
            value={maWindow}
          />
        </Col>
        <Col xs={24} xl={4}>
          <Typography.Text type="secondary">MA Color</Typography.Text>
          <Space className="ma-color-row" wrap>
            {MA_COLORS.map((color) => (
              <Button
                aria-label={`MA color ${color}`}
                className={maColor === color ? 'color-swatch is-active' : 'color-swatch'}
                disabled={!maVisible}
                key={color}
                onClick={() => onMaColorChange(color)}
                shape="circle"
                style={{ backgroundColor: color }}
              />
            ))}
          </Space>
        </Col>
      </Row>
    </div>
  );
}
