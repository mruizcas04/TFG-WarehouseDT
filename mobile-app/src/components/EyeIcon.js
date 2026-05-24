import React from 'react';
import { View } from 'react-native';

export default function EyeIcon({ visible = true, color = '#888', size = 20 }) {
  const w = size * 1.0;
  const h = size * 0.58;

  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View style={{
        width: w,
        height: h,
        borderRadius: h / 2,
        borderWidth: 1.5,
        borderColor: color,
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
      }}>
        {visible ? (
          <View style={{
            width: size * 0.32,
            height: size * 0.32,
            borderRadius: size * 0.16,
            backgroundColor: color,
          }} />
        ) : (
          <View style={{
            width: w + 4,
            height: 1.5,
            backgroundColor: color,
            borderRadius: 1,
          }} />
        )}
      </View>
    </View>
  );
}
