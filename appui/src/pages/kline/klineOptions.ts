import type { SelectProps } from 'antd/es/select';

import {
  LANGUAGE_OPTIONS,
  type CandleColorScheme,
  type Language,
  type PriceScale,
} from '../../store/configSlice';

export const scaleOptions: SelectProps<PriceScale>['options'] = [
  { value: 'normal', label: 'Normal' },
  { value: 'logarithmic', label: 'Logarithmic' },
];

export const colorSchemeOptions: SelectProps<CandleColorScheme>['options'] = [
  { value: 'china', label: 'China' },
  { value: 'international', label: 'International' },
];

export const languageOptions: SelectProps<Language>['options'] = LANGUAGE_OPTIONS.map((option) => ({
  ...option,
}));
