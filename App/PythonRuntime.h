#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface PythonRuntime : NSObject

+ (nullable NSString *)start;

+ (NSString *)callMethod:(NSString *)method payload:(NSString *)payload;

@end

NS_ASSUME_NONNULL_END
